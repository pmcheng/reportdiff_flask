import sqlite3,os
from flask import g, current_app

from flask import render_template, flash, redirect, url_for
from flask.ext.login import current_user
from ..models import User
from . import reports
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
        numreports=query_db("select count(*) as count from study where "+querystring,one=True)
        lastreport=query_db("select max(timestamp) as lasttime from study where final is not null and ("+querystring+")",one=True)
        avscore=query_db("select avg(diff_score_percent) as avscore from study where "+querystring,one=True)
        
        bins=query_db("""select case when diff_score_percent<10 then 1
                                   when diff_score_percent>=10 and diff_score_percent<25 then 2
                                   when diff_score_percent>=25 and diff_score_percent<50 then 3
                                   when diff_score_percent>=50 then 4
                               end as bin,
                               count(1) as c
                               from study where """+querystring+""" group by bin order by bin""")
        data=[item[1] for item in bins if item[0] is not None]
        chartID="histogram"
        chart= {"renderTo": chartID, "type":'column'}
        series= [{"name":'Studies',"data":data}]
        xAxis= {"categories": ['<10%', '10-25%', '25-50%', '>50%']}
        yAxis= {"title": {"text": 'Number of reports'}}
        title= {"text": 'Histogram of edit score'}
        
        return render_template('reports/index.html',numreports=numreports, lastreport=lastreport, avscore=avscore,
            chartID=chartID, chart= chart, series=series, title=title,
                                 xAxis=xAxis, yAxis=yAxis)
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
    report=query_db("select * from study where accession like '%s'" % accession, one=True)
    
    diff_match_patch.Diff_Timeout=0
    dmp=diff_match_patch.diff_match_patch()
    
    d=dmp.diff_main(report["prelim"],report["final"])
    dmp.diff_cleanupSemantic(d)
    diff=dmp.diff_prettyHtml(d)

    return render_template('reports/accession.html',report=report, diff=diff)