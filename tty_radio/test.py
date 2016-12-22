#!/usr/bin/env python
from time import sleep
from tty_radio.radio import Radio

if __name__ == "__main__":
    r = Radio()
    print('r:%s' % r)
    print('r.stations:%s' % r.stations)
    r.play()
    r.set('favs')
    print('r.station:%s' % r.station)
    print('r._station:%s' % r._station)
    print('r._station.streams:%s' % r._station.streams)
    # r.set('favs', 'DEF CON Radio')
    r.set('favs', 'BAGeL Radio')
    print('Playing')
    r.play()
    while r.song is None:
        sleep(1)
    print('r.song:%s' % r.song)
    print('Stopping')
    r.stop()
    r.set('favs', 'WCPE Classical')
    print('r.stream:%s' % r.stream)
    print('r._stream:%s' % r._stream)
    print('Playing')
    r.play()
    sleep(10)
    print('Stopping')
    r.stop()
