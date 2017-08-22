from moviepy.editor import *
from moviepy.video.tools.segmenting import findObjects
import youtube_dl
from celery import Celery
from os.path import basename
import io
import time
import datetime
from contextlib import redirect_stdout
# import redis

# red = redis.StrictRedis()

def hms_to_seconds(t):
    return sum(int(i) * 60**index for index, i in enumerate(t.split(":")[::-1]))


class ColeVideoCreator(object):
    def __init__(self):
        self.compositing_pattern = ImageClip('./cole-pattern-480.png')
        self.compositing_regions = findObjects(self.compositing_pattern)
        self.start_clip = VideoFileClip('./videos_480/01-start.mp4')
        self.cole_lean_clip = VideoFileClip('./videos_480/02-cole-lean.mp4')
        self.tv_3_clip = VideoFileClip('./videos_480/tv-extended.mp4')
        self.watching_tv_clip = VideoFileClip('./videos_480/04-watching.mp4')
        self.albert_clip = VideoFileClip('./videos_480/06-albert-glance.mp4')
        self.wth_clip = VideoFileClip('./videos_480/07-wth.mp4')

    def create_cole_video(self, tv_file_name, output_filename='./comp.mp4'):
        tv_clip = VideoFileClip(tv_file_name, audio=True)
        # grab the audio from the user's video so we can play it
        # throughout the final video
        tv_audio = tv_clip.audio
        tv_clip.audio = None

        clips = []
        clips.append(self.turn_on_tv_clip(tv_clip))
        if tv_clip.duration >= 20:
            clips.append(self.cole_lean_clip)
            elapsed = self.start_clip.duration + self.cole_lean_clip.duration
            clips.append(self.hold_on_tv_clip(tv_clip.subclip(elapsed-1, 15)))
            clips.append(self.albert_clip)
            clips.append(self.hold_on_tv_clip(tv_clip.subclip(15+self.albert_clip.duration, tv_clip.duration-1)))
        elif tv_clip.duration >= self.start_clip.duration + self.cole_lean_clip.duration:
            clips.append(self.cole_lean_clip)
            elapsed = self.start_clip.duration + self.cole_lean_clip.duration
            clips.append(self.hold_on_tv_clip(tv_clip.subclip(elapsed-1, tv_clip.duration-1)))
        clips.append(self.wth_clip)

        final_clip = concatenate_videoclips(clips, method='compose')
        tv_audio = tv_audio.volumex(0.25)
        final_audio = CompositeAudioClip(
            [tv_audio.set_start(1), final_clip.audio]
        )
        final_clip.audio = final_audio
        # final_clip.resize(0.25)
        final_clip.write_videofile(output_filename, fps=24, preset="ultrafast")
        # clean up to prevent zombie ffmpeg processes
        tv_clip.reader.close()
        self.start_clip.reader.close()
        self.cole_lean_clip.reader.close()
        self.tv_3_clip.reader.close()
        self.watching_tv_clip.reader.close()
        self.albert_clip.reader.close()
        self.wth_clip.reader.close()


        self.start_clip.audio.reader.close_proc()
        self.cole_lean_clip.audio.reader.close_proc()
        self.tv_3_clip.audio.reader.close_proc()
        self.watching_tv_clip.audio.reader.close_proc()
        self.albert_clip.audio.reader.close_proc()
        self.wth_clip.audio.reader.close_proc()

        tv_clip.__del__()
        self.start_clip.__del__()
        self.cole_lean_clip.__del__()
        self.tv_3_clip.__del__()
        self.watching_tv_clip.__del__()
        self.albert_clip.__del__()
        self.wth_clip.__del__()

        return output_filename

    def turn_on_tv_clip(self, tv_clip):
        start_tv = tv_clip.subclip(0, self.start_clip.duration-1)
        clips = [
            self.start_clip,
            start_tv.set_start(1)
        ]
        first_shot = self.comp_clips(clips)
        return first_shot

    def hold_on_tv_clip(self, tv_clip):
        clips = [
            self.tv_3_clip.subclip(0, tv_clip.duration),
            tv_clip
        ]
        third_shot = self.comp_clips(clips)
        return third_shot

    def comp_clips(self, clips):
        comp_clips = [
            c.resize(r.size).set_mask(r.mask).set_pos(r.screenpos)
            for c, r in zip(clips, self.compositing_regions)
        ]
        comp_result = CompositeVideoClip(comp_clips, self.compositing_pattern.size)
        return comp_result


class YoutubeDownloader(object):

    def __init__(self, url):
        self.options = {
            'format': 'best[height<=480]/best',
            # 'format': 'best'
            # 'download_archive': './video_download_archive',
            'outtmpl': './youtube_downloads/%(title)s.%(ext)s',
            'progress_hooks': [self.progress_hook]
        }
        self.url = url

    def progress_hook(self, d):
        print("progress hook d:", d)
        if d['status'] == 'finished':
            print("yt dl finished, now creating:", d['filename'])
            self.filename = d['filename']
            # create_cole_video_task.delay(d['filename'])

    def dl(self):
        with youtube_dl.YoutubeDL(self.options) as ydl:
            print("downloading:", self.url)
            print("options:", self.options)
            ydl.download([self.url])
            print("yt dl returning:", self.filename)
            return self.filename

    def good_length(self):
        test_options = {
            'simulate': True,
            'quiet': True,
            'forceduration': True
        }
        f = io.StringIO()
        with redirect_stdout(f):
            with youtube_dl.YoutubeDL(test_options) as ydl:
                ydl.download([self.url])
        output = f.getvalue()
        print("output:", output)
        duration_seconds = hms_to_seconds(output.strip())
        return duration_seconds <= 60


#celery_app = Celery('create_video', backend='redis://localhost', broker='pyamqp://guest@localhost//')
celery_app = Celery('create_video', backend='redis://localhost', broker='redis://localhost')


@celery_app.task
def youtube_download(url):
    downloader = YoutubeDownloader(url)
    path = downloader.dl()
    return path


@celery_app.task(bind=True)
def create_cole_video_task(self, path):
    print("video task path:", path)
    filename = basename(path)
    output_filename = './gordon_cole_gen/static/videos/' + filename
    creator = ColeVideoCreator()
    outpath = creator.create_cole_video(path, output_filename=output_filename)
    del creator
    public_path = '/static/videos/' + filename
    # red.publish('video-'+self.request.id, 'reload')
    return public_path
