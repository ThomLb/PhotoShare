######################################
# author ben lawson <balawson@bu.edu>
# Edited by: Craig Einstein <einstein@bu.edu>
######################################
# Some code adapted from
# CodeHandBook at http://codehandbook.org/python-web-application-development-using-flask-and-mysql/
# and MaxCountryMan at https://github.com/maxcountryman/flask-login/
# and Flask Offical Tutorial at  http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
# see links for further understanding
###################################################

import flask
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
import flask_login

#for image uploading
import os, base64

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

#These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'cs460MYSQL#23'
app.config['MYSQL_DATABASE_DB'] = 'photoshare'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

#begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email from Users")
users = cursor.fetchall()

def getUserList():
	cursor = conn.cursor()
	cursor.execute("SELECT email from Users")
	return cursor.fetchall()

class User(flask_login.UserMixin):
	pass

@login_manager.user_loader
def user_loader(email):
	users = getUserList()
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	return user

@login_manager.request_loader
def request_loader(request):
	users = getUserList()
	email = request.form.get('email')
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	cursor = mysql.connect().cursor()
	cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email))
	data = cursor.fetchall()
	pwd = str(data[0][0] )
	user.is_authenticated = request.form['password'] == pwd
	return user

'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
	return new_page_html
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
	if flask.request.method == 'GET':
		return '''
			   <form action='login' method='POST'>
				<input type='text' name='email' id='email' placeholder='email'></input>
				<input type='password' name='password' id='password' placeholder='password'></input>
				<input type='submit' name='submit'></input>
			   </form></br>
		   <a href='/'>Home</a>
			   '''
	#The request method is POST (page is recieving data)
	email = flask.request.form['email']
	cursor = conn.cursor()
	#check if email is registered
	if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
		data = cursor.fetchall()
		pwd = str(data[0][0] )
		if flask.request.form['password'] == pwd:
			user = User()
			user.id = email
			flask_login.login_user(user) #okay login in user
			return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

	#information did not match
	return "<a href='/login'>Try again</a>\
			</br><a href='/register'>or make an account</a>"

@app.route('/logout')
def logout():
	flask_login.logout_user()
	return render_template('hello.html', message='Logged out')

@login_manager.unauthorized_handler
def unauthorized_handler():
	return render_template('unauth.html')

#you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register", methods=['GET'])
def register():
	return render_template('register.html', supress='True')

@app.route("/register", methods=['POST'])
def register_user():
	try:
		email=request.form.get('email')
		password=request.form.get('password')
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('register'))
	cursor = conn.cursor()
	test =  isEmailUnique(email)
	if test:
		print(cursor.execute("INSERT INTO Users (email, password) VALUES ('{0}', '{1}')".format(email, password)))
		conn.commit()
		#log user in
		user = User()
		user.id = email
		flask_login.login_user(user)
		return render_template('hello.html', name=email, message='Account Created!')
	else:
		print("couldn't find all tokens")
		return flask.redirect(flask.url_for('register'))

def getUsersPhotos(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures WHERE user_id = '{0}'".format(uid))
	return cursor.fetchall() #NOTE return a list of tuples, [(imgdata, pid, caption), ...]

def getUserIdFromEmail(email):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
	return cursor.fetchone()[0]

def isEmailUnique(email):
	#use this to check if a email has already been registered
	cursor = conn.cursor()
	if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)):
		#this means there are greater than zero entries with that email
		return False
	else:
		return True
#end login code

@app.route('/profile')
@flask_login.login_required
def protected():
	return render_template('hello.html', name=flask_login.current_user.id, message="Here's your profile")

#begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		imgfile = request.files['photo']
		caption = request.form.get('caption')
		photo_data =imgfile.read()
		cursor = conn.cursor()
		cursor.execute('''INSERT INTO Pictures (imgdata, user_id, caption) VALUES (%s, %s, %s )''', (photo_data, uid, caption))
		conn.commit()
		addActivityScore(uid)
		return render_template('hello.html', name=flask_login.current_user.id, message='Photo uploaded!', photos=getUsersPhotos(uid), base64=base64)
	#The method is GET so we return a  HTML form to upload the a photo.
	else:
		return render_template('upload.html')
#end photo uploading code

#code for handling friendships
@app.route('/addfriend', methods=['POST'])
def createFriendship():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	uid2 = request.form.get('uid2')
	cursor = conn.cursor()
	cursor.execute("INSERT INTO Friendship (UID1, UID2)  VALUES %s, %s", uid, uid2)
	conn.commit()
	return

@app.route("/search", methods=['GET'])
def	getUsers():
	return render_template('userlist.html', name=flask_login.current_user.id, message="Here's a list of all users", users=getAllUsers())

@app.route("/friendlist", methods=['GET'])
def displayList():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	return render_template('friendList.html', name=flask_login.current_user.id, message="Here's your friends list", friends=getFriendList(uid))

def getFriendList():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute("SELECT * FROM Friendship WHERE uid1 = {0}".format(uid))
	return cursor.fetchall()

def getAllUsers():
	cursor = conn.cursor()
	cursor.execute("SELECT * FROM Users")
	return cursor.fetchall()

def addActivityScore(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT COUNT(user_id) FROM Pictures WHERE user_id = {0}".format(uid))
	numPhotos = cursor.fetchall()
	cursor.execute("SELECT COUNT(user_id) FROM Comments WHERE user_id = {0}".format(uid))
	numComments = cursor.fetchall()
	score = numPhotos + numComments
	cursor.execute("UPDATE Users SET u_score = {0} WHERE uid = {1}".format(score, uid))
	conn.commit()
	return

def getTopTenUsers():
	cursor = conn.cursor()
	cursor.execute("SELECT TOP 10 u_score FROM Users ORDER BY u_score DESC")
	return cursor.fetchall()
#end handling friendships code

#Album and Photo code
def getAllPhotos():
	cursor = conn.cursor()
	cursor.execute("SELECT * FROM Pictures")
	return cursor.fetchall() #NOTE return a list of tuples, [(imgdata, pid, caption), ...]

app.route('/album', method=['POST'])
@flask_login.login_required
def album():
	name = request.form.get('name')
	uid = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute('''INSERT INTO Albums (name, uid) VALUES (%s, %s )''', (name, uid))
	conn.commit()
	return render_template('hello.html', name=flask_login.current_user.id, message='Album created!')

app.route('/deletepicture', methods=['POST'])
@flask_login.login_required
def deletePicture():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	img_data = request.form.get('data')
	cursor = conn.cursor()
	cursor.execute("DELETE FROM Pictures WHERE imgdata = {0}".format(img_data))
	conn.commit()
	addActivityScore(uid)
	return render_template('hello.html', name=flask_login.current_user.id, message='Picture deleted!')

app.route('/deletealbum', methods=['POST'])
@flask_login.login_required
def deleteAlbum():
	name = request.form.get('name')
	cursor = conn.cursor()
	cursor.execute("DELETE FROM Pictures FROM FULL JOIN Albums ON Pictures.album_id = Albums.album_id WHERE name = {0}".format(name))
	cursor.execute("DELETE FROM Albums WHERE name = {0}".format(name))
	conn.commit()
	return
#end Album and Photo code

#Tag management code
app.route('/selftag', methods=['GET'])
@flask_login.login_required
def getMyTags():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	name = request.form.get('name')
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata FROM Picture WHERE user_id = {1} AND picture_id IN (SELECT picture_id FROM (Tags FULL JOIN Tagged ON Tags.tag_id = Tagged.tag_id) WHERE name = {0})".format(name, uid))
	photos = cursor.fetchall()
	return render_template('tag.html', name=flask_login.current_user.id, message='Self tagged photos!', photos1=photos)

app.route('/publictag', methods=['GET'])
@flask_login.login_required
def getMyTags():
	name = request.form.get('name')
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata FROM Pictures WHERE picure_id IN (SELECT Picture_id FROM Tagged FULL JOIN Tags ON Tags.tag_id = Tagged.tag_id WHERE name = {0})".format(name))
	photos = cursor.fetchall()
	return render_template('tag.html', name=flask_login.current_user.id, message='All tagged photos!', photo2=photos)

app.route('/populartag', methods=['GET'])
@flask_login.login_required
def getPopularTags():
	cursor = conn.cursor()
	cursor.execute("SELECT COUNT(name) FROM Tags ORDER BY name DESC LIMIT 3")
	return cursor.fetchall()

app.route('/searchphotos', methods=['GET'])
def photoSeach():
	tags = request.form.get('tags')
	tags = tags.split(" ")
	cursor = conn.cursor()
	photos = cursor.execute("SELECT imgdata FROM Picture LEFT JOIN Tagged ON Picture.picture_id IN (SELECT picture_id FROM (Tagged FULL JOIN Tags ON Tagged.tag_id = Tags.tagi_id) WHERE name in {0})".format(tags))
	return render_template('searcphotos.html', name=flask_login.current_user.id, message='Searched tagged photos!', photo3=photos)
#end Tag management code

#Comments code
def addComment():
	comment = request.form.get('comment')
	cursor = conn.cursor()
	cursor.execute("INSERT INTO Comments (text) VALUES (%s)", comment)
	conn.commit()
	if flask.current_user.is_authenticated:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		addActivityScore(uid)
	return

def like():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute("INSERT INTO Likes (user_id) VALUES (%s)", uid)
	conn.commit()
	return

app.route('/displaylikes', methods=['GET'])
def displaylikes():
	cursor = conn.cursor()
	cursor.execute("SELECT COUNT(user_id) FROM Likes")
	numLikes = cursor.fetchall()
	cursor.execute("SELECT user_id FROM Likes")
	users = cursor.fetchall()
	return render_template('displaylikes.html', message='Likes info!', likesCount=numLikes, users=users)

def searchComments():
	comment = request.form.get('comment')
	cursor = conn.cursor()
	cursor.execute("SELECT fname, lname FROM Users INNER JOIN Comments ON Users.user_id = Comments.user_id WHERE Comments.text = {0}".format(comment))
	comments = cursor.fetchall()
	return render_template('comment.html', message='Comment searched!', results=comments)

#Recommendations code
app.route('/recs', methods=['GET'])
def recommendation():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute("SELECT uid2 FROM Friendships WHERE uid1 = {0} AND uid2 = (SELECT uid2 WHERE uid1 = (SELECT uid2 WHERE uid1 = {0}))".format(uid))
	recs = cursor.fetchall()
	return render_template('recs.html', message='Your recs!', recommendations=recs)

@app.route('/maylike', methods=['GET'])
def mayLike():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute("SELECT TOP 3 name FROM Tags INNER JOIN Tagged ON Tags.tag_id = Tagged.tag_id WHERE picture_id FROM Tagged = (SELECT picture_id FROM Pictures WHERE user_id = {0}) ORDERY BY name DESC".format(uid))
	tags = cursor.fetchall()
	
	return
#end Recommendations code


#default page
@app.route("/", methods=['GET'])
def hello():
	#display all photos on homepage
	#display the top 10 users
	return render_template('hello.html', message='Welcome to Photoshare', topTen = getTopTenUsers(), allPhotos=getAllPhotos())


if __name__ == "__main__":
	#this is invoked when in the shell  you run
	#$ python app.py
	app.run(port=5000, debug=True)
