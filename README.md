# ReportDiff_Flask

### *Review and analysis of attending edits of radiology trainee reports*
 
ReportDiff is a system designed to provide automated feedback for resident dictated reports.  This repository is the web server component of the project, based on the Flask web microframework.  The ReportDiff system consists of several components:

* A retrieval script queries the Powerscribe server and retrieves trainee-signed preliminary reports every few minutes.  It also periodically queries the server for final versions of cached preliminary reports.  It computes the edit differences between preliminary and final reports.
* R scripts are used to analyze aggregate report data.
* A web service (ReportDiff_Flask) presents the reports and edit scores generated by the retriever.

The system was presented as an educational exhibit at the 2015 meeting of the Radiological Society of North America (RSNA), where the presentation received a *magna cum laude* award.

The server runs within a Python virtual environment (using the venv module).  The main configuration is in the SQLite database file location as given by config.py.  It should not be difficult to adapt the scripts to use a more robust database.

This project uses code from the following open source projects:

* [Python Flask](http://flask.pocoo.org/)
* [Google diff-match-patch](https://github.com/google/diff-match-patch)
* [Bootstrap](http://getbootstrap.com)

The project also uses the Highcharts JS library under a free non-commercial license:
* [Highcharts](http://www.highcharts.com/)
