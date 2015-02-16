import json
import uuid

import flask

from datetime import datetime

from configobj import ConfigObj
from flask.ext.sqlalchemy import SQLAlchemy

# Config
config = ConfigObj('config.ini')
dburl = config['dburl']

app = flask.Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = dburl
db = SQLAlchemy(app)


# DB Section
class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    resid = db.Column(db.String, unique=True)
    desc = db.Column(db.Text)
    owner = db.Column(db.String)
    ip = db.Column(db.String)
    created = db.Column(db.DateTime)

    def __init__(self, owner, desc, ip="LOCAL"):
        self.resid = uuid.uuid4().hex
        self.desc = desc
        self.owner = owner
        self.ip = ip
        self.created = datetime.utcnow()

    def __repr__(self):
        return '<Project %r>' % self.id


class Response(db.Model):
    __tablename__ = 'responses'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    response = db.Column(db.Text)
    created = db.Column(db.DateTime)

    def __init__(self, proj_id, response):
        self.project_id = proj_id
        self.response = response
        self.created = datetime.utcnow()

    def __repr__(self):
        return '<Response %r Project ID %r> %r' % (self.id, self.project_id,
                                                   self.response)


# Routes
@app.route('/')
def index():

    return flask.render_template('index.html')


@app.route('/retrieve/<resid>')
def retrieve(resid):
    project = get_project(resid)
    if not project:
        return 'Not Found', 404

    return flask.Response(json.dumps(project), mimetype='application/json')


@app.route('/request', methods=['POST'])
def request():
    if flask.request.method != 'POST':
        return 'Unsupported method', 405
    form = flask.request.form
    if 'desc' and 'owner' not in form:
        return 'Missing data', 400
    owner = form['owner']
    desc = form['desc']
    ip = flask.request.environ['REMOTE_ADDR']

    proj = Project(owner, desc, ip)
    db.session.add(proj)
    db.session.commit()

    resid = proj.resid
    return flask.Response(resid, mimetype='text/plain')


# Miscs
def get_project(resid):
    p = Project.query.filter_by(resid=resid).limit(1).all()
    if not p:
        return None
    p = p[0]
    project = {}
    project['desc'] = p.desc
    project['created'] = p.created.strftime('%Y-%m-%d %H:%m:%S UTC')
    project['resid'] = p.resid
    project['owner'] = p.owner
    project['responses'] = []

    r = Response.query.filter_by(project_id=p.id).all()
    for x in r:
        c = x.created.strftime('%Y-%m-%d %H:%m:%S UTC')
        project['responses'].append({'response': x.response, 'date': c})

    if len(project['responses']) == 0:
        project['status'] = 'Open'
    elif len(project['responses']) == 1:
        project['status'] = 'Responded'
    else:
        project['status'] = 'Updated'

    return project


if __name__ == '__main__':
    app.run(debug=True)
