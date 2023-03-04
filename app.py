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

import operator
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
app.config['MYSQL_DATABASE_PASSWORD'] = 'cs460MYSQL23'
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
	return render_template('loggedout.html', message='Logged out')

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
		lname=request.form.get('lname')
		fname=request.form.get('fname')
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('register'))
	cursor = conn.cursor()
	test =  isEmailUnique(email)
	if test:
		print(cursor.execute("INSERT INTO Users (email, password, fname, lname) VALUES ('{0}', '{1}', '{2}', '{3}')".format(email, password, lname, fname)))
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
	uid = getUserIdFromEmail(flask_login.current_user.id)
	return render_template('user.html', name=flask_login.current_user.id, message="Here's your profile", score=addActivityScore(uid))

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
		return render_template('hello.html', name=flask_login.current_user.id, message='Photo uploaded!', photos=getUsersPhotos(uid), base64=base64)
	#The method is GET so we return a  HTML form to upload the a photo.
	else:
		return render_template('upload.html')
#end photo uploading code

#code for handling friendships
@app.route("/addfriend", methods=['POST'])
def createFriendship():
	uid2=request.form.get('uid2')
	uid1 = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute("INSERT INTO Friendship (uid1, uid2)  VALUES (%s, %s)", (uid1, uid2))
	conn.commit()
	return render_template('friendList.html', name=flask_login.current_user.id, message='Friends List', friends=getFriendList(uid1))

#search.html should be the profile of the other user
@app.route("/search", methods=['GET'])
def	getUsers():
	return render_template('userlist.html', message='Here\'s a list of all users', users=getAllUsers())

@app.route("/friendlist", methods=['GET'])
def displayList():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	return render_template('friendList.html', name=flask_login.current_user.id, message='Friends List', friends=getFriendList(uid))

def getFriendList(uid1):
	cursor = conn.cursor()
	cursor.execute("SELECT fname FROM Users WHERE user_id IN (SELECT uid2 FROM Friendship WHERE uid1 = {0})".format(uid1))
	return cursor.fetchall()

def getAllUsers():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute("SELECT fname, lname, user_id, email FROM Users WHERE user_id <> '{0}'".format(uid))
	return cursor.fetchall()

def addActivityScore(uid):
	cursor = conn.cursor()
	numPhotos = cursor.execute("SELECT COUNT(picture_id) FROM Pictures WHERE user_id = {0}".format(uid))
	numComments = cursor.execute("SELECT COUNT(text) FROM Comments WHERE user_id = {0}".format(uid))
	score = numPhotos + numComments
	cursor.execute("UPDATE Users SET u_score = {0} WHERE user_id = {1}".format(score, uid))
	conn.commit()
	return score

def getTopTenUsers():
	cursor = conn.cursor()
	cursor.execute("SELECT email FROM Users ORDER BY u_score DESC LIMIT 3")
	return cursor.fetchall()
#end handling friendships code

#Album and Photo code
@app.route("/yourphotos", methods=['GET'])
def usersPhotos():
	#display users photos
	uid = getUserIdFromEmail(flask_login.current_user.id)
	return render_template('yourphotos.html', message='Your photos:', allPhotos=getUsersPhotos(uid), base64=base64)

def getAllPhotos():
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures")
	return cursor.fetchall() #NOTE return a list of tuples, [(imgdata, pid, caption), ...]

def getAlbumNames():
	cursor = conn.cursor()
	cursor.execute("SELECT album_name, album_id FROM Albums")
	return cursor.fetchall()

@app.route('/album', methods=['POST'])
@flask_login.login_required
def album():
	name = request.form.get('album')
	uid = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute('''INSERT INTO Albums (album_name, user_id) VALUES (%s, %s )''', (name, uid))
	conn.commit()
	return render_template('album.html', name=flask_login.current_user.id, message='Album created!', albums=getAlbumNames())

@app.route("/albumnames", methods=['GET'])
def albumnames():
	return render_template('album.html', name=flask_login.current_user.id, message='Album created!', albums=getAlbumNames())

@app.route('/deletepicture', methods=['POST'])
@flask_login.login_required
def deletePicture():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	data = request.form.get('deletepicture')
	cursor = conn.cursor()
	cursor.execute("DELETE FROM Pictures WHERE picture_id = {0}".format(data))
	conn.commit()
	return render_template('yourphotos.html', name=flask_login.current_user.id, message='Photo deleted!', allPhotos=getUsersPhotos(uid), base64=base64)

@app.route('/deletealbum', methods=['POST'])
@flask_login.login_required
def deleteAlbum():
	albID = request.form.get('deletealbum')
	cursor = conn.cursor()
	cursor.execute("DELETE FROM Pictures WHERE album_id = {0}".format(albID))
	conn.commit()
	cursor.execute("DELETE FROM Albums WHERE album_id = {0}".format(albID))
	conn.commit()
	return render_template('album.html', name=flask_login.current_user.id, message='Album deleted!')
#end Album and Photo code

#Tag management code
@app.route('/addtags', methods=['POST'])
@flask_login.login_required
def tags():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	pic_id = request.form.get('photoTagged')
	name = request.form.get('addtag')
	cursor = conn.cursor()
	cursor.execute('''INSERT INTO Tags (tag_name, picture_id) VALUES (%s, %s)''', (name, pic_id))
	conn.commit()
	return render_template('yourphotos.html', message='Tag created!', allPhotos=getUsersPhotos(uid), base64=base64)

@app.route('/selftag', methods=['POST'])
@flask_login.login_required
def getMyTags():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	name = request.form.get('mytag')
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures WHERE user_id = {1} AND picture_id = (SELECT picture_id FROM Tags WHERE tag_name = {0})".format(name, uid))
	photos = cursor.fetchall()
	return render_template('tag.html', message='Photos tagged with' + name + '!', photos=photos, base64=base64)

@app.route('/publictag', methods=['POST'])
@flask_login.login_required
def getPublicTags():
	name = request.form.get('public')
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures WHERE picture_id = (SELECT picture_id FROM Tags WHERE tag_name = {0})".format(name))
	photos = cursor.fetchall()
	return render_template('tag.html', message='All tagged photos!', photos=photos, base64=base64)

def getPopularTags():
	cursor = conn.cursor()
	cursor.execute("SELECT tag_name, COUNT(tag_name) AS value FROM Tags GROUP BY tag_name ORDER BY value DESC LIMIT 3")
	return cursor.fetchall()

@app.route('/searchphotos', methods=['POST'])
def photoSeach():
	tags = request.form.get('conjuctive')
	# tags = tags.split()
	length = len(tags.split())
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures WHERE picture_id IN (SELECT picture_id FROM Tags WHERE tag_name IN ({0}) GROUP BY picture_id HAVING COUNT(picture_id) = {1} )".format(tags, length))
	photos = cursor.fetchall()
	return render_template('tag.html', message='Results!', photos=photos, base64=base64)
#end Tag management code

#Comments code
@app.route('/addcomment', methods=['POST'])
def addComment():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	picID = request.form.get('pic')
	comment = request.form.get('comment')
	cursor = conn.cursor()
	cursor.execute("INSERT INTO Comments (text, user_id, picture_id) VALUES (%s, %s, %s)", (comment, uid, picID))
	conn.commit()
	# if flask_login.confirm_login:
	# 	addActivityScore()
	return render_template('hello.html', message='Comment added!', comment=comment, photos=getAllPhotos(), base64=base64)

@app.route('/addlike', methods=['POST'])
@flask_login.login_required
def like():
	photoID = request.form.get('photo')
	uid = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute("INSERT INTO Likes (user_id, picture_id) VALUES (%s, %s)", (uid, photoID))
	conn.commit()
	return

@app.route('/displaylikes', methods=['GET'])
def displaylikes():
	pic_id = request.forms.get('pic')
	cursor = conn.cursor()
	cursor.execute("SELECT COUNT(user_id) FROM Likes WHERE picture_id = {0}".format(pic_id))
	numLikes = cursor.fetchall()
	cursor.execute("SELECT fname, lname FROM Users WHERE user_id IN (SELECT user_id FROM Likes WHERE picture_id = {0})".format(pic_id))
	users = cursor.fetchall()
	cursor.execute("SELECT imgdata, caption FROM Pictures WHERE picture_id = {0}".format(pic_id))
	photo = cursor.fetchall()
	return render_template('likes.html', likesCount=numLikes, users=users)

@app.route('/searchcomment', methods=['POST'])
def searchComments():
	comment = request.form.get('comment')
	cursor = conn.cursor()
	cursor.execute("SELECT fname, lname FROM Users WHERE user_id IN (SELECT user_id FROM Comments WHERE text = '{0}')".format(comment))
	commentors = cursor.fetchall()
	return render_template('likes.html', message='Comment searched!', users2=commentors)

#Recommendations code
@app.route('/recommendation', methods=['POST'])
def recommendation():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute("SELECT fname, lname FROM Users WHERE user_id IN (SELECT uid2 FROM Friendship WHERE uid1 IN (SELECT uid2 FROM Friendship WHERE uid1 = {0})) GROUP BY user_id ORDER BY COUNT(user_id) DESC".format(uid))
	recs = cursor.fetchall()
	return render_template('user.html', message='Found possible recommendations', recs=recs)

@app.route('/maylike', methods=['POST'])
def mayLike():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute("SELECT tag_name FROM Tags WHERE picture_id IN (SELECT picture_id FROM Pictures WHERE user_id = {0}) GROUP BY tag_id ORDER BY COUNT(tag_id) DESC LIMIT 3".format(uid))
	tags = cursor.fetchall()
	listTags = ()
	for tag in tags:
		listTags += tag
	cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures WHERE picture_id IN (SELECT picture_id FROM Tags WHERE tag_name IN {0} GROUP BY picture_id ORDER BY COUNT(picture_id) DESC)".format(listTags))
	photos = cursor.fetchall()
	return render_template('user.html', message='You may like!', mayLike=photos, base64=base64)
#end Recommendations code


#default page
@app.route("/", methods=['GET'])
def hello():
	#display all photos on homepage
	#display the top 10 users
	return render_template('hello.html', message='Welcome to Photoshare', topThree=getTopTenUsers(), popTags=getPopularTags(), photos=getAllPhotos(), base64=base64)


if __name__ == "__main__":
	#this is invoked when in the shell  you run
	#$ python app.py
	app.run(port=5000, debug=True)
