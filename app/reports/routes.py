import sqlite3,os
#from flask import g, current_app

from flask import render_template, flash, redirect, url_for
from flask.ext.login import current_user
from ..models import User, ReportView, Report
from .. import db
from . import reports
import datetime
import diff_match_patch
from sqlalchemy import or_, and_, func
 
#def get_db():   
#    rdb = getattr(g, '_database', None)
#    if rdb is None:
#        rdb = g._database = sqlite3.connect(current_app.config['REPORT_DATABASE'])
#    rdb.row_factory = sqlite3.Row
#    return rdb
#
#def query_db(query, args=(), one=False):
#    cur = get_db().execute(query, args)
#    rv = cur.fetchall()
#    cur.close()
#    return (rv[0] if rv else None) if one else rv    
#
#@reports.teardown_request
#def close_connection(exception):
#    rdb = getattr(g, '_database', None)
#    if rdb is not None:
#        rdb.close()

@reports.route('/')
def index():
    if current_user.is_authenticated():
        #querystring="attendingID={0} or residentID={0}".format(current_user.ps_id)

        #numreports=query_db("select count(*) as count from study where "+querystring,one=True)[0]
        numreports=db.session.query(func.count(Report.accession)).filter(or_(Report.attendingID==current_user.ps_id, Report.residentID==current_user.ps_id)).first()[0]
        
        #lastreport=query_db("select max(timestamp) as lasttime from study where final is not null and ("+querystring+")",one=True)[0]
        lastreport=db.session.query(func.max(Report.timestamp)).filter(and_(Report.final!=None,or_(Report.attendingID==current_user.ps_id, Report.residentID==current_user.ps_id))).first()[0]
        #avscore=query_db("select avg(diff_score_percent) as avscore from study where "+querystring,one=True)[0]
        if numreports>0: 
            avscore=db.session.query(func.avg(Report.diff_score_percent)).filter(or_(Report.attendingID==current_user.ps_id, Report.residentID==current_user.ps_id)).first()[0]
        else:
            avscore=0
        
        #histoquery="select case "
        
        bars=11
        categories=[]
        data=[0]*bars
        barsize=100/(bars-1)
        cases=db.session.query(Report.diff_score_percent).filter(and_(Report.diff_score_percent!=None, or_(Report.attendingID==current_user.ps_id, Report.residentID==current_user.ps_id)))
        for case in cases:
            bin=int(case[0]//barsize)
            if bin>(bars-1):
                bin=bars-1
            data[bin]+=1
        
        for i in range(bars-1):
            limit_low=i*barsize
            limit_high=limit_low+barsize
            #histoquery+="when diff_score_percent>={0} and diff_score_percent<{1} then {2} ".format(limit_low,limit_high,i)
            categories.append("{0}-{1}%".format(limit_low,limit_high))
        #histoquery+="when diff_score_percent>=100 then {0} ".format(bars-1)
        categories.append(">100%")
        #histoquery+="end as bin, count(1) as c from study where {0} group by bin order by bin".format(querystring)
        #bins=query_db(histoquery)
        
        #for item in bins:
        #    if item[0] is not None:
        #        data[item[0]]=item[1]
                
        histogram_json={
            'chart': {'type':'column'},
            'title': {'text': 'Diff Percent Distribution'},
            'series': [{'name':'Studies','data':data}],
            'xAxis': {'categories': categories},
            'yAxis': {'title': {'text': 'Number of reports'}},
            'credits': {'enabled':False}

        }
        
        
        return render_template('reports/index.html',numreports=numreports, lastreport=lastreport, avscore=avscore,
            histogram_json=histogram_json)
    else:
        return render_template('reports/index.html')

#def buildquery(userstring):
#    return "attending like '%"+userstring+"%' or resident like '%"+userstring+"%'"

@reports.route('/user/<username>/comparison')
def comparison(username):
    user = User.query.filter_by(username=username).first()
    if user!=current_user: 
        flash('Cannot access requested page.')
        return redirect(url_for('reports.index'))
    #attendingquery="select attendingID, avg(diff_score_percent) from study where attendingID is not NULL group by attendingID"
    #attendingresult=query_db(attendingquery)
    attendingresult=db.session.query(Report.attendingID, func.avg(Report.diff_score_percent).label('average')).filter(Report.attendingID!=None).group_by(Report.attendingID)
    attendingscores={} # (attendingID) => average diff_score_percent
    for item in attendingresult:
        attendingscores[int(item.attendingID)]=float(item.average)
    attendingsorted=sorted(attendingscores.items(),key=lambda x:x[1],reverse=True)
    
    #studyquery="select residentID, attendingID, sum(diff_score_percent), count(*) as count from study where residentID is not NULL and attendingID is not NULL group by residentID, attendingID"
    #studyresult=query_db(studyquery)
    studyresult=db.session.query(Report.residentID, Report.attendingID, func.sum(Report.diff_score_percent).label('sum'), func.count(Report.diff_score_percent).label('count')).filter(and_(Report.attendingID!=None,Report.residentID!=None)).group_by(Report.residentID,Report.attendingID)
    studyscores={}  # (residentID, attendingID) => total diff_score_percent
    studycounts={}  # (residentID, attendingID) => study count
    for item in studyresult:
        #studyscores[(int(item[0]),int(item[1]))]=float(item[2])
        studyscores[(int(item.residentID),int(item.attendingID))]=float(item.sum)
        #studycounts[(int(item[0]),int(item[1]))]=float(item[3])
        studycounts[(int(item.residentID),int(item.attendingID))]=int(item.count)
    
    for key in studyscores:
        studyscores[key]-=attendingscores[key[1]]*studycounts[key]  # adjust scores for mean attending edit score
    
    residentscores={}
    by_attending={}
    for key in studyscores:
        test_user=User.query.filter_by(ps_id=key[0]).first()
        if test_user.grad_date!=user.grad_date: continue
        if str(key[0]) in residentscores:
            residentscores[str(key[0])]+=studyscores[key]
        else:
            residentscores[str(key[0])]=studyscores[key]   
            
        if test_user==user:
            by_attending[str(key[1])]=studyscores[key]/studycounts[key]
    
    data=sorted(residentscores.items(),key=lambda x:x[1],reverse=True)
    
    
    
    resident_names=[]
    for item in data:
        test_user=User.query.filter_by(ps_id=item[0]).first()
        if test_user is not None and test_user==user:
            if test_user.nickname.strip()!="":
                resident_names.append(test_user.nickname+" "+test_user.lastname)
            else:
                resident_names.append(test_user.firstname+" "+test_user.lastname)
        else:
            resident_names.append('')
            
    by_attending_data=sorted(by_attending.items(),key=lambda x:x[1],reverse=True)
    attending_names=[]
    for item in by_attending_data:
        test_user=User.query.filter_by(ps_id=item[0]).first()
        if test_user is not None:
            if test_user.nickname.strip()!="":
                attending_names.append(test_user.nickname+" "+test_user.lastname)
            else:
                attending_names.append(test_user.firstname+" "+test_user.lastname)
        else:
            resident_names.append('')
    
    
    resident_chart_json={
            'chart': {'type':'bar'},
            'title': {'text': 'Within class summed adjusted edit scores (lower is better)'},
            'xAxis': {'title': {'text': 'Trainees'},'categories': resident_names},
            'yAxis': {'title': {'text': 'Summed adjusted edit score'}},
            'series': [{'name':'Edit scores','data':data}],
            'tooltip': {'enabled':False},
            'legend' : {'enabled':False},
            'credits': {'enabled':False}
        }

    attending_chart_json={
            'chart': {'type':'bar'},
            'title': {'text': 'Average adjusted edit score by attending (lower is better)'},
            'xAxis': {'title': {'text': 'Attendings'},'categories': attending_names},
            'yAxis': {'title': {'text': 'Average adjusted edit score'}},
            'series': [{'name':'Edit scores','data':by_attending_data}],
            'tooltip': {'enabled':False},
            'legend' : {'enabled':False},
            'credits': {'enabled':False}
        }
        
    
    return render_template('reports/comparison.html',resident_chart_json=resident_chart_json,resident_table_height=len(data),
                            attending_chart_json=attending_chart_json,attending_table_height=len(by_attending_data))
    
@reports.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first()
    if user!=current_user: 
        flash('Cannot access requested page.')
        return redirect(url_for('reports.index'))
        
    #querystring="attendingID={0} or residentID={0}".format(current_user.ps_id)
    #query="select accession, timestamp, proceduredescription, attending, resident, diff_score_percent from study where diff_score is not null and ("+querystring+") order by timestamp desc"
    #reports=query_db(query)
    reports=Report.query.filter(Report.diff_score!=None).filter(or_(Report.attendingID==current_user.ps_id, Report.residentID==current_user.ps_id)).order_by(Report.timestamp.desc())
    return render_template('reports/user.html',user=user,reports=reports)

@reports.route('/accession/<accession>')    
def accession(accession):
    if not current_user.is_authenticated():
        flash('Cannot access requested page.')
        return redirect(url_for('reports.index'))
    
    #report=query_db("select * from study where accession like '%s'" % accession, one=True)
    report=Report.query.filter(Report.accession==accession).first()
    
    if report is None:
        return redirect('/user/'+current_user.username)

    #if report["prelim"] is None or report["final"] is None:
    if report.prelim is None or report.final is None:
        return redirect('/user/'+current_user.username)
       
    # Need to be an author of the report to view it
    #if report["attendingID"]!=current_user.ps_id and report["residentID"]!=current_user.ps_id:
    if report.attendingID!=current_user.ps_id and report.residentID!=current_user.ps_id:
        return redirect('/user/'+current_user.username)

    # Add view to the repot viewing log   
    report_view = ReportView(user_id=current_user.id,accession=accession,timestamp=datetime.datetime.now())
    db.session.add(report_view)
    db.session.commit()
    
    dmp=diff_match_patch.diff_match_patch()
    dmp.Diff_Timeout=0
    
    d=dmp.diff_main(report.prelim,report.final)
    dmp.diff_cleanupSemantic(d)
    diff=dmp.diff_prettyHtml(d)

    return render_template('reports/accession.html',report=report, diff=diff)