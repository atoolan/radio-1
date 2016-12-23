from __future__ import print_function
import platform
PY3 = False
if platform.python_version().startswith('3'):
    PY3 = True
import sys
import textwrap
import os
import subprocess
import re
import math
from time import sleep
from io import StringIO
if PY3:
    get_input = input
else:
    get_input = raw_input

from . import (
    VOL,
    COMPACT_TITLES)
from .color import colors, THEME
from .banner import bannerize
from .album import gen_art
from .api import Client


# TODO
#   windows detect terminal size
#   leverage Radio/Station class to simplify menu "other stations"
#       aka station switch selections
#


def stream_list(streams):
    exploded = []
    name_re = re.compile("name=(.*),url")
    desc_re = re.compile("desc=\"(.*)\",art")
    for s in streams:
        name_m = name_re.search(s)
        desc_m = desc_re.search(s)
        s_exp = {
            'name': name_m.group(1),
            'desc': desc_m.group(1),
            'repr': s
        }
        exploded.append(s_exp)
    return exploded


def print_streams(station, streams, stations):
    (term_w, term_h) = term_hw()
    line_cnt = 0
    if len(streams) == 0:
        print("Exiting, empty station file, delete it and rerun")
        sys.exit(1)
    # set up to pretty print station data
    # get left column width
    name_len = max([len(s['name']) for s in streams]) + 1
    # the first line has the name
    # each subsequent line has whitespace up to column begin mark
    # print the stations
    i = 0
    for s in streams:
        prefix = (" %2d" % i + " ) " + s['name'] +
                  ' ' * (name_len - len(s['name'])))
        (w, h) = print_blockify(
            prefix, THEME['ui_names'],
            s['desc'], THEME['ui_desc'])
        line_cnt += h
        i += 1
    # TODO get rid of hard coded access to the other stations
    prefix = (" %2d" % len(streams) + " ) SomaFM" +
              ' ' * (name_len - len("SomaFM")))
    desc = ("Enter " + str(len(streams)) +
            " or 's' to show SomaFM streams")
    if station == "soma":
        prefix = (" %2d" % len(streams) + " ) Favorites" +
                  ' ' * (name_len - len("Favorites")))
        desc = ("Enter " + str(len(streams)) +
                " or 'f' to show favorite streams")
    (w, h) = print_blockify(
        prefix, THEME['ui_names'],
        desc, THEME['ui_desc'])
    line_cnt += h
    return line_cnt - 1


# \033[A moves cursor up 1 line
# ' ' overwrites text
# '\b' resets cursor to start of line
# if the term is narrow enough, you need to go up multiple lines
def del_prompt(num_chars):
    # determine lines to move up, there is at least 1
    # bc user pressed enter to give input
    # when they pressed Enter, the cursor went to beginning of the line
    (term_w, term_h) = term_hw()
    move_up = int(math.ceil(float(num_chars) / float(term_w)))
    print("\033[A" * move_up + ' ' * num_chars + '\b' * (num_chars), end='')


def term_hw():
    (w, h) = (80, 40)
    try:
        # TODO os agnostic tty size
        # *nix get terminal/console width
        rows, columns = os.popen('stty size', 'r').read().split()
    except ValueError:
        return (w, h)
    try:
        w = int(columns)
        h = int(rows)
    except ValueError:
        pass
    # print("term width: %d"% width)
    return (w, h)


def read_input():
    try:
        stream_num = get_input("\nPlease select a stream [q to quit]: ")
    except SyntaxError:
        return
    if not stream_num:
        return
    stream_num = str(stream_num).strip().lower()
    if len(stream_num) == 0:
        return
    return stream_num


def try_as_int(stream_num, station, max_val):
    try:
        stream_num = int(stream_num)
    except ValueError:
        return None
    # keys[len] is the other station
    if stream_num < 0 or stream_num > max_val:
        return None
    # the final row is not a stream, but a station change
    if stream_num == max_val:
        if station == 'favs':
            return (None, 'soma')
        # else station == 'soma'
        return (None, 'favs')
    return (stream_num, station)


def get_choice(station, streams):
    """Get user choice of stream to play, or station to change"""
    while True:
        stream_num = read_input()
        if stream_num is None:
            continue
        ctrl_char = stream_num[0]
        if ctrl_char not in ['q', 'e', 's', 'f']:
            retval = try_as_int(stream_num, station, len(streams))
            if retval is None:
                continue
            else:
                return retval
        if (ctrl_char == 'q' or ctrl_char == 'e'):
            return (None, 'q')
        if ctrl_char == 'f':
            return (None, 'favs')
        if ctrl_char == 's':
            return (None, 'soma')
    # should never be here


def ui():
    # set term title
    sys.stdout.write("\x1b]0;" + "~=radio tuner=~" + "\x07")
    c = Client()
    do_another = True
    next_st = 'favs'
    while do_another:
        try:
            next_st = ui_loop(c, next_st)
        except KeyboardInterrupt:
            do_another = False
        if next_st == 'q':
            do_another = False
    # clear term title
    sys.stdout.write("\x1b]0;" + "\x07")


def ui_loop(client, station='favs'):
    """list possible stations, read user input, and call player"""
    # when the player is exited, this loop happens again
    c = client
    if station is None:
        station = c.stations()[0]
    deets = c.station(station)
    streams = stream_list(c.streams(station))
    stations = c.stations()
    # streams.sort()  # put in alpha order
    # ######
    # print stations
    (term_w, term_h) = term_hw()
    banner_txt = deets['ui_name'] + ' Tuner'
    with colors(THEME['ui_banner']):
        (banner, font) = bannerize(banner_txt, term_w)
        b_IO = StringIO(banner)
        b_h = len(b_IO.readlines())
        print(banner)
        b_h += 1
    line_cnt = print_streams(station, streams, stations)
    loop_line_cnt = line_cnt + b_h + 2
    loop_line_cnt += 1
    if term_h > loop_line_cnt:
        print('\n' * (term_h - loop_line_cnt - 1))
    (stream_num, station) = get_choice(station, streams)
    if station == 'q':
        return 'q'
    # no stream given, must have been a station change, refresh list
    if stream_num is None:
        return station
    # ######
    # otherwise stream num specified, so call player
    ##
    # get the stream name only
    to_stream = streams[stream_num]
    # convert the name only into more details
    stream = c.stream(station, to_stream['name'])
    if stream is None:
        print('Error, could not get stream details')
        return station
    display_album(stream['art'])
    display_banner(stream['name'])
    display_metadata(c, stream)
    c.stop()
    # TODO poll user input to send stop
    return station


def display_metadata(client, stream):
    # to test these updates against another stream
    #   without conflicting audio:
    #   mpg123 -f 0 -C -@ <url>
    c = client
    station_name = stream['station']
    stream_name = stream['name']
    station_stream = (station_name, stream_name)
    c.play(station_stream)
    i = 0
    disp_name = stream['meta_name']
    # disp names of '', like DEF CON Radio will escape loop
    while i < 10 and disp_name is None:
        stream = c.stream(station_name, stream_name)
        disp_name = stream['meta_name']
        sleep(0.5)
        i += 1
    if disp_name is None:
        disp_name = stream_name
    if disp_name is not None and disp_name != '':
        print_blockify(
            THEME['meta_prefix_str'], THEME['meta_prefix'],
            disp_name, THEME['meta_stream_name'])
    # wait for initial song
    i = 0
    song_len = 0
    song_name = stream['meta_song']
    # song names of '', like WCPE will escape loop
    while i < 10 and song_name is None:
        stream = c.stream(station_name, stream_name)
        song_name = stream['meta_song']
        sleep(0.5)
        i += 1
    if song_name is not None and song_name != '':
        song_len = print_blockify(
            THEME['meta_prefix_str'], THEME['meta_prefix'],
            song_name, THEME['meta_song_name'],
            wrap=False)[0]
    # keep polling for song title changes
    do_another = True
    while do_another:
        status = c.status()
        song_now = status['song']
        if song_now != song_name and song_now is not None and song_now != '':
            if COMPACT_TITLES and song_len > 0:
                del_prompt(song_len)
            song_len = print_blockify(
                THEME['meta_prefix_str'], THEME['meta_prefix'],
                song_now, THEME['meta_song_name'],
                wrap=False)[0]
            song_name = song_now
        is_playing = status['currently_streaming']
        if not is_playing:
            return
        sleep(1)


def print_blockify(prefix='', prefix_color='endc',
                   blk='', blk_color='endc',
                   wrap=True):
    # NOTE won't print only prefix without blk
    if len(blk) == 0:
        return (0, 0)
    p_len = len(prefix)
    with colors(prefix_color):
        # sys.stdout.write && flush
        print(prefix, end='')
    (term_w, term_h) = term_hw()
    lines = textwrap.wrap(blk, term_w - p_len)
    max_blk_len = len(lines[0])
    with colors(blk_color):
        print(lines[0])
    if not wrap:
        return (len(prefix) + max_blk_len, 1)
    # prefix only appears on 1st line, justifying remainder
    prefix = ' ' * p_len
    for line in lines[1:]:
        if len(line) > max_blk_len:
            max_blk_len = len(line)
        with colors(blk_color):
            print(prefix + line)
    return (max_blk_len, len(lines))


def display_album(art_url):
    if art_url is None or art_url == '':
        return
    (term_w, term_h) = term_hw()
    art = gen_art(art_url, term_w, term_h)
    if art is None:
        return
    print("ASCII Printout of Station's Logo:")
    print(art)


def display_banner(stream_name):
    unhappy = True
    while unhappy:
        (term_w, term_h) = term_hw()
        font = "unknown"
        with colors(THEME['stream_name_banner']):
            (banner, font) = bannerize(stream_name, term_w)
            b_IO = StringIO(banner)
            b_height = len(b_IO.readlines())
            if term_h > (b_height + 3):  # Playing, Station Name, Song Title
                print('\n' * (term_h - b_height - 2))
            print(banner, end='')
        with colors(THEME['stream_name_confirm']):
            prompt = "Press enter if you like banner"
            prompt += " (font: " + font + "), else any char then enter "
            try:
                happiness = get_input(prompt)
            except SyntaxError:
                happiness = ''
            del_prompt(len(prompt) + len(happiness))
            if len(happiness) == 0:
                unhappy = False
                msg1 = "Playing stream, enjoy..."
                msg2 = "[pause/quit=q; vol=+/-]"
                if term_w > (len(msg1) + len(msg2)):
                    print(msg1 + ' ' + msg2)
                else:
                    print(msg1)
                    print(msg2)
            else:
                print("")  # empty line for pretty factor


def old_filter(stream, parse_name, parse_song, pr_blk):  # noqa
    def do_mpg123(url, prefix, show_deets=1):
        # mpg123 command line mp3 stream player
        # does unbuffered output, so the subprocess...readline snip works
        # -C allows keyboard presses to send commands:
        #    space is pause/resume, q is quit, +/- control volume
        # -@ tells it to read (for stream/playlist info) filenames/URLs from url
        subp_cmd = ["mpg123", "-f", VOL, "-C", "-@", url]
        try:
            p = subprocess.Popen(
                subp_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
        except OSError as e:
            raise Exception('OSError %s when executing %s' % (e, subp_cmd))
        delete_cnt = 0
        has_deeted = False
        has_titled = False
        for line in iter(p.stdout.readline, b''):
            out = bytes.decode(line)
            out = out.strip()
            if show_deets and not has_deeted and out[0:8] == "ICY-NAME":
                parsed = parse_name(out[10:])
                if parsed is not None:
                    pr_blk(parsed, prefix)
                has_deeted = True
            elif out[0:8] == "ICY-META":
                parsed = parse_song(out[10:])
                # confine song title to single line to look good
                song_title = pr_blk(parsed, prefix, chomp=True, do_pr=False)
                # this will delete the last song, and reuse its line
                # (so output only has one song title line)
                if COMPACT_TITLES:
                    if has_titled:
                        del_prompt(delete_cnt)
                    else:
                        has_titled = True
                print(song_title)
                sys.stdout.flush()
                delete_cnt = len(song_title)
        return delete_cnt
    # end do_mpg123

    replay = True
    show_station_deets = True
    while replay:
        with colors(THEME['meta_prefix']):
            prefix = THEME['meta_prefix_str']
            delete_cnt = do_mpg123(
                stream[0],
                prefix,
                show_station_deets)
            del_prompt(delete_cnt)
        with colors(THEME['stream_exit_confirm']):
            # it will reach here anytime the player stops executing
            # (eg it has an exp, failure, etc)
            # but ideally it'll only reach here when the user presses
            # q (exiting the player) to "pause" it
            # you can't use mpg123's 'pause' cmd (spacebar) bc it'll
            # fail a minute or two after resuming (buffer errors)
            # for some reason it literally pauses the music,
            # buffering the stream until unpaused
            # behavior we want is to stop recving the stream
            # (like turning off a radio)
            prompt = "Paused. Press enter to Resume; q to quit. "
            reloop = get_input(prompt)
            # if the user inputs anything other than pressing
            # return/enter, then loop will quit
            if len(reloop) != 0:
                replay = False
            else:
                # for prettiness we don't want to reprint the station
                # details (name, etc) upon replaying within this loop
                show_station_deets = False
                # we also want to get rid of that prompt
                # to make room for the song name data again
                del_prompt(len(prompt) + len(prefix))
                sys.stdout.flush()
                # this play->pause->loop should never accumulate lines
                # in the output (except for the first Enter they press
                # at a prompt and even then, it's just an empty line)
