import sqlite3,os
from flask import g, current_app

from flask import render_template, flash, redirect, url_for
from flask.ext.login import current_user
from ..models import User, ReportView
from .. import db
from . import reports
import datetime
import diff_match_patch
 
def get_db():   
    rdb = getattr(g, '_database', None)
    if rdb is None:
        rdb = g._database = sqlite3.connect(current_app.config['REPORT_DATABASE'])
    rdb.row_factory = sqlite3.Row
    return rdb

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv    

@reports.teardown_request
def close_connection(exception):
    rdb = getattr(g, '_database', None)
    if rdb is not None:
        rdb.close()

@reports.route('/')
def index():
    if current_user.is_authenticated():
        #userstrings=current_user.userstrings.split('|')
        #querystring=""
        #for (i,userstring) in enumerate(userstrings):
        #    if i>0: querystring+=" or "
        #    querystring+=buildquery(userstring)
        querystring="attendingID={0} or residentID={0}".format(current_user.ps_id)
        numreports=query_db("select count(*) as count from study where "+querystring,one=True)[0]
        lastreport=query_db("select max(timestamp) as lasttime from study where final is not null and ("+querystring+")",one=True)[0]
        avscore=query_db("select avg(diff_score_percent) as avscore from study where "+querystring,one=True)[0]
        
        if avscore is None:
            avscore=0
        
        histoquery="select case "
        
        bars=11
        categories=[]
        data=[0]*bars
        barsize=100/(bars-1)
        for i in range(bars-1):
            limit_low=i*barsize
            limit_high=limit_low+barsize
            histoquery+="when diff_score_percent>={0} and diff_score_percent<{1} then {2} ".format(limit_low,limit_high,i)
            categories.append("{0}-{1}%".format(limit_low,limit_high))
        histoquery+="when diff_score_percent>=100 then {0} ".format(bars-1)
        categories.append(">100%")
        histoquery+="end as bin, count(1) as c from study where {0} group by bin order by bin".format(querystring)
        bins=query_db(histoquery)
        
        for item in bins:
            if item[0] is not None:
                data[item[0]]=item[1]
                
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

def buildquery(userstring):
    return "attending like '%"+userstring+"%' or resident like '%"+userstring+"%'"
    
@reports.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first()
    if user!=current_user: 
        flash('Cannot access requested page.')
        return redirect(url_for('reports.index'))
        
    #userstrings=user.userstrings.split('|')
    #querystring=""
    #for (i,userstring) in enumerate(userstrings):
    #    if i>0: querystring+=" or "
    #    querystring+=buildquery(userstring)
    querystring="attendingID={0} or residentID={0}".format(current_user.ps_id)
    query="select accession, timestamp, proceduredescription, attending, resident, diff_score_percent from study where diff_score is not null and ("+querystring+") order by timestamp desc"
    reports=query_db(query)
    return render_template('reports/user.html',user=user,reports=reports)

@reports.route('/accession/<accession>')    
def accession(accession):
    if not current_user.is_authenticated():
        flash('Cannot access requested page.')
        return redirect(url_for('reports.index'))
    
    report=query_db("select * from study where accession like '%s'" % accession, one=True)
    
    if report is None:
        return redirect('/user/'+current_user.username)
    if report["attendingID"]!=current_user.ps_id and report["residentID"]!=current_user.ps_id:
        return redirect('/user/'+current_user.username)
    if report["prelim"] is None or report["final"] is None:
        return redirect('/user/'+current_user.username)
        
    report_view = ReportView(user_id=current_user.id,accession=accession,timestamp=datetime.datetime.now())
    db.session.add(report_view)
    db.session.commit()
    
    dmp=diff_match_patch.diff_match_patch()
    dmp.Diff_Timeout=0
    
    d=dmp.diff_main(report["prelim"],report["final"])
    dmp.diff_cleanupSemantic(d)
    diff=dmp.diff_prettyHtml(d)

    return render_template('reports/accession.html',report=report, diff=diff)