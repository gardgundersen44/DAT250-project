"""Provides all routes for the Social Insecurity application.

This file contains the routes for the application. It is imported by the app package.
It also contains the SQL queries used for communicating with the database.
"""

from pathlib import Path

from flask import flash, redirect, render_template, send_from_directory, url_for, session

from app import app, sqlite
from app.forms import CommentsForm, FriendsForm, IndexForm, PostForm, ProfileForm

@app.route("/", methods=["GET", "POST"])
@app.route("/index", methods=["GET", "POST"])
def index():
    """Provides the index page for the application.

    It reads the composite IndexForm and based on which form was submitted,
    it either logs the user in or registers a new user.

    If no form was submitted, it simply renders the index page.
    """
    index_form = IndexForm()
    login_form = index_form.login
    register_form = index_form.register

    if login_form.validate_on_submit() and login_form.submit.data:
        get_user = """
            SELECT *
            FROM Users
            WHERE username = ?;
            """

        user = sqlite.connection.execute(get_user, (login_form.username.data,)).fetchone()

        if user is None:
            flash("Sorry, this user does not exist!", category="warning")
        elif user["password"] != login_form.password.data:
            flash("Sorry, wrong password!", category="warning")
        elif user["password"] == login_form.password.data:
            session["username"] = login_form.username.data
            return redirect(url_for("stream", username=login_form.username.data))

    elif register_form.is_submitted() and register_form.submit.data:
        insert_user = """
            INSERT INTO Users (username, first_name, last_name, password)
            VALUES (?, ?, ?, ?);
            """
        sqlite.connection.execute(insert_user, 
                                    (register_form.username.data, 
                                    register_form.first_name.data, 
                                    register_form.last_name.data, 
                                    register_form.password.data))
        sqlite.connection.commit()
        flash("User successfully created!", category="success")
        return redirect(url_for("index"))
    return render_template("index.html.j2", title="Welcome", form=index_form)

@app.route("/stream/<string:username>", methods=["GET", "POST"])
def stream(username: str):
    """Provides the stream page for the application.

    If a form was submitted, it reads the form data and inserts a new post into the database.

    Otherwise, it reads the username from the URL and displays all posts from the user and their friends.
    """
    logged_in_user = session.get("username")

    if logged_in_user != username:
        flash("Unauthorized access!", category="warning")
        return redirect(url_for("index"))

    post_form = PostForm()
    get_user = """
        SELECT *
        FROM Users
        WHERE username = ?;
        """
    user = sqlite.connection.execute(get_user, (username,)).fetchone()

    if post_form.is_submitted():
        if post_form.image.data:
            path = Path(app.instance_path) / app.config["UPLOADS_FOLDER_PATH"] / post_form.image.data.filename
            post_form.image.data.save(path)

        insert_post = """
            INSERT INTO Posts (u_id, content, image, creation_time)
            VALUES (?, ?, ? , CURRENT_TIMESTAMP);
            """
        sqlite.connection.execute(insert_post, (user["id"], post_form.content.data, post_form.image.data.filename))
        sqlite.connection.commit()
        return redirect(url_for("stream", username=username))

    get_posts = """
         SELECT p.*, u.*, (SELECT COUNT(*) FROM Comments WHERE p_id = p.id) AS cc
         FROM Posts AS p JOIN Users AS u ON u.id = p.u_id
         WHERE p.u_id IN (SELECT u_id FROM Friends WHERE f_id = ?) OR p.u_id IN (SELECT f_id FROM Friends WHERE u_id = ?) OR p.u_id = ?
         ORDER BY p.creation_time DESC;
        """
    posts = sqlite.connection.execute(get_posts, (user["id"], user["id"], user["id"]))
    return render_template("stream.html.j2", title="Stream", username=username, form=post_form, posts=posts)

@app.route("/comments/<string:username>/<int:post_id>", methods=["GET", "POST"])
def comments(username: str, post_id: int):
    """Provides the comments page for the application.

    If a form was submitted, it reads the form data and inserts a new comment into the database.

    Otherwise, it reads the username and post id from the URL and displays all comments for the post.
    """
    logged_in_user = session.get("username")

    if logged_in_user != username:
        flash("Unauthorized access!", category="warning")
        return redirect(url_for("index"))

    comments_form = CommentsForm()
    get_user = """
        SELECT *
        FROM Users
        WHERE username = ?;
        """
    user = sqlite.connection.execute(get_user, (username,)).fetchone()

    if comments_form.is_submitted():
        insert_comment = """
            INSERT INTO Comments (p_id, u_id, comment, creation_time)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP);
            """
        sqlite.connection.execute(insert_comment, (post_id, user["id"], comments_form.comment.data))
        sqlite.connection.commit()

    get_post = """
        SELECT *
        FROM Posts AS p JOIN Users AS u ON p.u_id = u.id
        WHERE p.id = ?;
        """
    get_comments = """
        SELECT DISTINCT *
        FROM Comments AS c JOIN Users AS u ON c.u_id = u.id
        WHERE c.p_id=?
        ORDER BY c.creation_time DESC;
        """
    post = sqlite.connection.execute(get_post, (post_id)).fetchone()
    comments = sqlite.connection.execute(get_comments, (post_id,)).fetchall()
    return render_template("comments.html.j2", title="Comments", username=username, form=comments_form, post=post, comments=comments)

@app.route("/friends/<string:username>", methods=["GET", "POST"])
def friends(username: str):
    """Provides the friends page for the application.
    If a form was submitted, it reads the form data and inserts a new friend into the database.
    Otherwise, it reads the username from the URL and displays all friends of the user.
    """
    logged_in_user = session.get("username")
    if logged_in_user != username:
        flash("Unauthorized access!", category="warning")
        return redirect(url_for("index"))
    friends_form = FriendsForm()
    get_user = """
        SELECT *
        FROM Users
        WHERE username = ?;
        """
    user = sqlite.connection.execute(get_user, (username,)).fetchone()
    if friends_form.is_submitted():
        get_friend = """
            SELECT *
            FROM Users
            WHERE username = ?;
            """
        friend = sqlite.connection.execute(get_friend, (friends_form.friend.data,)).fetchone()
        get_friends = """
            SELECT f_id
            FROM Friends
            WHERE u_id = ?;
            """
        friends = sqlite.connection.execute(get_friends, (user["id"],)).fetchall()
        if friend is None:
            flash("User does not exist!", category="warning")
        elif friend["id"] == user["id"]:
            flash("You cannot be friends with yourself!", category="warning")
        elif friend["id"] in [friend["f_id"] for friend in friends]:
            flash("You are already friends with this user!", category="warning")
        else:
            insert_friend = """
                INSERT INTO Friends (u_id, f_id)
                VALUES (?, ?);
                """
            sqlite.connection.execute(insert_friend, (user["id"], friend["id"]))
            sqlite.connection.commit()
            flash("Friend successfully added!", category="success")
    get_friends = """
        SELECT *
        FROM Friends AS f JOIN Users as u ON f.f_id = u.id
        WHERE f.u_id = ? AND f.f_id != ?;
        """
    friends = sqlite.connection.execute(get_friends, (user["id"], user["id"])).fetchall()
    return render_template("friends.html.j2", title="Friends", username=username, friends=friends, form=friends_form)

@app.route("/profile/<string:username>", methods=["GET", "POST"])
def profile(username: str):
    """
    Provides the profile page for the application.
    If a form was submitted, it reads the form data and updates the user's profile in the database.
    Otherwise, it reads the username from the URL and displays the user's profile.
    """
    logged_in_user = session.get("username")
    if logged_in_user != username:
        flash("Unauthorized access!", category="warning")
        return redirect(url_for("index"))
    profile_form = ProfileForm()
    get_user = """
        SELECT *
        FROM Users
        WHERE username = ?;
        """
    user = sqlite.connection.execute(get_user, (username,)).fetchone()

    if profile_form.is_submitted():
        update_profile = """
            UPDATE Users
            SET education=?, employment=?,
                music=?, movie=?,
                nationality=?, birthday=?
            WHERE username=?;
            """
        sqlite.connection.execute(update_profile, 
                                  (profile_form.education.data,
                                   profile_form.employment.data,
                                   profile_form.music.data,
                                   profile_form.movie.data,
                                   profile_form.nationality.data,
                                   profile_form.birthday.data,))
        sqlite.connection.commit()
        return redirect(url_for("profile", username=username))

    return render_template("profile.html.j2", title="Profile", username=username, user=user, form=profile_form)

@app.route("/uploads/<string:filename>")
def uploads(filename):
    """Provides an endpoint for serving uploaded files."""
    return send_from_directory(Path(app.instance_path) / app.config["UPLOADS_FOLDER_PATH"], filename)
