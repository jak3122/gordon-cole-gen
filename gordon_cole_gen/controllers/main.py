from flask import Blueprint, render_template, flash, request, redirect, url_for, Response
from flask_login import login_user, logout_user, login_required

from gordon_cole_gen.extensions import cache
from gordon_cole_gen.forms import LoginForm
from gordon_cole_gen.models import User
from gordon_cole_gen.create_video import youtube_download, create_cole_video_task, celery_app, YoutubeDownloader
from celery.result import AsyncResult
from celery import chain
# import redis
# import threading

main = Blueprint('main', __name__)
# red = redis.StrictRedis()


@main.route('/')
@cache.cached(timeout=1000)
def home():
    return render_template('index.html')


@main.route('/upload', methods=["POST"])
def upload():
    if request.method == 'POST':
        yt_url = request.form['youtube-link']
        is_good_length = YoutubeDownloader(yt_url).good_length()
        if is_good_length:
            task = chain(youtube_download.s(yt_url) | create_cole_video_task.s())()
            task_id = task.id
            return redirect('/result/' + task_id)
        else:
            flash("Video must be less than 1 minute in length.")
            return redirect('/')
    return render_template('index.html')


@main.route('/result/<id>')
def result(id):
    res = celery_app.AsyncResult(id)
    is_ready = res.ready()
    print("result:", res)
    print("id:", res.id)
    print("ready:", is_ready)
    print("state:", res.state)
    print("status:", res.status)
    if is_ready:
        video_src = res.get(timeout=1.0)
    else:
        video_src = None
    return render_template('result.html', is_ready=is_ready, video_src=video_src)


# @main.route('/stream')
# def stream():
#     return Response(event_stream(), mimetype="text/event-stream")


# def event_stream():
#     pubsub = red.pubsub()
#     pubsub.subscribe('video-*')
#     for message in pubsub.listen():
#         print ("event_stream message:", message)
#         yield 'data: {}\n\n'.format(message['data'])

