from flask import Flask, render_template, request, redirect, session, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from gtts import gTTS
import os
import datetime
import io
from sqlalchemy.sql import func

app = Flask(__name__)
app.secret_key = "secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///vocab.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(80))

class Vocabulary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100))
    meaning = db.Column(db.String(200))
    last_reviewed = db.Column(db.DateTime, default=func.now())
    interval = db.Column(db.Integer, default=1)
    next_review = db.Column(db.DateTime, default=func.now())
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))

with app.app_context():
    db.create_all()

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"], password=request.form["password"]).first()
        if user:
            session["user_id"] = user.id
            return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        user = User(username=request.form["username"], password=request.form["password"])
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        word = request.form["word"]
        meaning = request.form["meaning"]
        vocab = Vocabulary(word=word, meaning=meaning, user_id=session["user_id"])
        db.session.add(vocab)
        db.session.commit()
    vocab_list = Vocabulary.query.filter_by(user_id=session["user_id"]).all()
    return render_template("dashboard.html", vocab_list=vocab_list)

@app.route("/review")
def review():
    if "user_id" not in session:
        return redirect(url_for("login"))
    now = datetime.datetime.utcnow()
    word = Vocabulary.query.filter(Vocabulary.user_id==session["user_id"], Vocabulary.next_review<=now).order_by(Vocabulary.next_review).first()
    return render_template("review.html", word=word)

@app.route("/answer/<int:id>", methods=["POST"])
def answer(id):
    correct = request.form["response"] == "y"
    word = Vocabulary.query.get(id)
    if correct:
        word.interval *= 2
    else:
        word.interval = 1
    word.last_reviewed = datetime.datetime.utcnow()
    word.next_review = word.last_reviewed + datetime.timedelta(days=word.interval)
    db.session.commit()
    return redirect(url_for("review"))

@app.route("/tts/<text>")
def tts(text):
    tts = gTTS(text)
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return send_file(fp, mimetype="audio/mp3")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
