DROP DATABASE photoshare;
CREATE DATABASE IF NOT EXISTS photoshare;
USE photoshare;
-- DROP TABLE IF EXISTS Pictures CASCADE;
-- DROP TABLE IF EXISTS Users CASCADE;
-- DROP TABLE IF EXISTS Albums CASCADE;
-- DROP TABLE IF EXISTS Comments CASCADE;
-- DROP TABLE IF EXISTS Likes CASCADE;
-- DROP TABLE IF EXISTS Tags CASCADE;
-- DROP TABLE IF EXISTS Tagged CASCADE;
-- DROP TABLE IF EXISTS Friendship CASCADE;


CREATE TABLE Users (
    user_id INT4 AUTO_INCREMENT,
    gender VARCHAR(6),
    email VARCHAR(255) UNIQUE,
    password VARCHAR(255),
    dob DATE,
    hometown VARCHAR(40),
    fname VARCHAR(40),
    lname VARCHAR(40),
    u_score INT,
    CONSTRAINT users_pk PRIMARY KEY (user_id)
);


CREATE TABLE Albums
( 
  album_id int4 AUTO_INCREMENT, 
  album_name VARCHAR(40) NOT NULL, 
  date_of_creation timestamp,
  user_id int4 NOT NULL,
  CONSTRAINT album_pk PRIMARY KEY (album_id),
  FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);


CREATE TABLE Pictures
(
  picture_id int4 AUTO_INCREMENT,
  user_id int4,
  imgdata longblob ,
  caption VARCHAR(255),
  album_id int4,
  INDEX upid_idx (user_id),
  CONSTRAINT pictures_pk PRIMARY KEY (picture_id),
  FOREIGN KEY (user_id) REFERENCES Users(user_id),
  FOREIGN KEY (album_id) REFERENCES Albums(album_id) ON DELETE CASCADE
);


CREATE TABLE Comments(
  comment_id int4 AUTO_INCREMENT,
  text varchar(10000),
  commentdate timestamp,
  user_id int4 NOT NULL,
  picture_id int4 NOT NULL,
  CONSTRAINT comment_pk PRIMARY KEY (comment_id),
  FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (picture_id) REFERENCES Pictures(picture_id) ON DELETE CASCADE
);

CREATE TABLE Likes(
  user_id int4,
  picture_id int4,
  CONSTRAINT likes_pk PRIMARY KEY (picture_id, user_id),
  FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
  FOREIGN KEY (picture_id) REFERENCES Pictures(picture_id) ON DELETE CASCADE
);

CREATE TABLE Tags(
  tag_id int4 AUTO_INCREMENT,
  tag_name varchar(100),
  CONSTRAINT tag_pk PRIMARY KEY (tag_id)
);

CREATE TABLE Tagged(
  picture_id int4,
  tag_id int4,
  CONSTRAINT tagged_pk PRIMARY KEY (picture_id, tag_id),
  FOREIGN KEY(picture_id) REFERENCES Pictures(picture_id),
  FOREIGN KEY(tag_id) REFERENCES Tags(tag_id)
);

CREATE TABLE Friendship (
    uid1 INT4,
    uid2 INT4,
    CHECK (uid1 <> uid2),
    CONSTRAINT friends_pk PRIMARY KEY (uid1 , uid2),
    FOREIGN KEY (uid1)
        REFERENCES Users (user_id)
        ON DELETE CASCADE,
    FOREIGN KEY (uid2)
        REFERENCES Users (user_id)
        ON DELETE CASCADE
);


INSERT INTO Users (email, password, fname, lname) VALUES ('test@bu.edu', 'test', 'first','last');
INSERT INTO Users (email, password, fname, lname) VALUES ('test1@bu.edu', 'test', 'name1', 'name2');
