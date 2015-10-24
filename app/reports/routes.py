import sqlite3,os

from flask import render_template, flash, redirect, url_for
from flask.ext.login import current_user
from ..models import User, ReportView, Report
from .. import db
from . import reports
import datetime
import diff_match_patch
from sqlalchemy import or_, and_, func
 
@reports.route('/')
def index():
    if current_user.is_authenticated():
        numreports=db.session.query(func.count(Report.accession)).filter(or_(Report.attendingID==current_user.ps_id, Report.residentID==current_user.ps_id)).first()[0]
        
        lastreport=db.session.query(func.max(Report.timestamp)).filter(and_(Report.final!=None,or_(Report.attendingID==current_user.ps_id, Report.residentID==current_user.ps_id))).first()[0]

        if numreports>0: 
            avscore=db.session.query(func.avg(Report.diff_score_percent)).filter(or_(Report.attendingID==current_user.ps_id, Report.residentID==current_user.ps_id)).first()[0]
        else:
            avscore=0
        
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
            categories.append("{0}-{1}%".format(limit_low,limit_high))
        categories.append(">100%")
                
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


@reports.route('/user/<username>/comparison')
def comparison(username):
    user = User.query.filter_by(username=username).first()
    if user!=current_user: 
        flash('Cannot access requested page.')
        return redirect(url_for('reports.index'))

    attendingresult=db.session.query(Report.attendingID, func.avg(Report.diff_score_percent).label('average')).filter(Report.attendingID!=None).group_by(Report.attendingID)
    attendingscores={} # (attendingID) => average diff_score_percent
    for item in attendingresult:
        attendingscores[int(item.attendingID)]=float(item.average)
    attendingsorted=sorted(attendingscores.items(),key=lambda x:x[1],reverse=True)
    
    studyresult=db.session.query(Report.residentID, Report.attendingID, func.sum(Report.diff_score_percent).label('sum'), func.count(Report.diff_score_percent).label('count')).filter(and_(Report.attendingID!=None,Report.residentID!=None)).group_by(Report.residentID,Report.attendingID)
    studyscores={}  # (residentID, attendingID) => total diff_score_percent
    studycounts={}  # (residentID, attendingID) => study count
    for item in studyresult:
        studyscores[(int(item.residentID),int(item.attendingID))]=float(item.sum)
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
    for n,item in enumerate(data):
        if item[0]==user.ps_id:
            
            if user.nickname.strip()!="":
                username=user.nickname+" "+user.lastname
            else:
                username=user.firstname+" "+user.lastname
            resident_names.append(username)
            data[n]={'name':username,'y':item[1],'color':'#ff0000'}
        else:
            resident_names.append('')
            data[n]=item[1]
            
    by_attending_data=sorted(by_attending.items(),key=lambda x:x[1],reverse=True)
    attending_names=[]
    for item in by_attending_data:
        test_user=User.query.filter_by(ps_id=item[0]).first()
        if test_user.nickname.strip()!="":
            attending_names.append(test_user.nickname+" "+test_user.lastname)
        else:
            attending_names.append(test_user.firstname+" "+test_user.lastname)
    
    
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
        
    reports=Report.query.filter(Report.diff_score!=None).filter(or_(Report.attendingID==current_user.ps_id, Report.residentID==current_user.ps_id)).order_by(Report.timestamp.desc())
    return render_template('reports/user.html',user=user,reports=reports)

@reports.route('/accession/<accession>')    
def accession(accession):
    if not current_user.is_authenticated():
        flash('Cannot access requested page.')
        return redirect(url_for('reports.index'))
    
    report=Report.query.filter(Report.accession==accession).first()
    
    if report is None:
        return redirect('/user/'+current_user.username)

    if report.prelim is None or report.final is None:
        return redirect('/user/'+current_user.username)
       
    # Need to be an author of the report to view it
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