#!/usr/bin/env python
# coding: utf-8

import os
import sys
from collections import defaultdict
from gmusicapi import Mobileclient
from pprint import pprint

_SHORTWORD = 4
_MATCHTHRESH = 20

def loadM3U(path):
    def _parseExtInf(line):
        line = line[8:] # strip off the #EXITNF: prefix
        length, title = line.split(',', 1)
        return int(length), title

    with open(sys.argv[1]) as f:
        playlist = [
            _parseExtInf(x) for x in
            [x for x in f.read().splitlines() if '#EXTINF' in x]
        ]

    return playlist


def getClient(rc=None):
    if rc is None:
        rc = os.environ['HOME'] + '/.gmusicrc'

    with open(rc) as f:
        user, pw = [(x.split('='))[1].strip() for x in f.readlines()]

    mc = Mobileclient()
    mc.login(user,pw, Mobileclient.FROM_MAC_ADDRESS)

    return mc

def getGMusicPlaylist(mc):
    gplaylist = None
    gplaylists = mc.get_all_user_playlist_contents()
    for gp in gplaylists:
        if gp['name'] == 'M3U imported':
            print "Removing old playlist"
            mc.delete_playlist(gp['id'])
            break

    print "Creating new playlist 'M3U imported'."
    return mc.create_playlist(
        'M3U imported',
        'Songs imported from M3U files.',
        False)

def getGLibrary(mc):
    # cache all existing songs in the library, index them
    library = {}
    index = defaultdict(lambda: defaultdict(int))

    for song in mc.get_all_songs():
        songid = song['id']
        library[songid] = song
        for word in song['title'].split():
            if len(word) < _SHORTWORD:
                continue
            index[word.lower()][songid] += 3
        for word in song['artist'].split():
            if len(word) < _SHORTWORD:
                continue
            index[word.lower()][songid] += 1

    return library, index

def findLockerBestMatch(song, library, index):
    # try and find a match locally, failing that, in AA
    matches = defaultdict(int)
    length, title = song
    for word in set(title.lower().split()):
        if len(word) < _SHORTWORD:
            continue
        if word in index:
            for songid, val in index[word].iteritems():
                matches[songid] += val

    def _l(sid):
        return int(library[sid]['durationMillis'])/1000

    matches = sorted(matches.iteritems(), key=lambda a: a[1])[-5:]
    matches2 = []
    for songid, _ in matches:
        # check song length
        lenscore = (_l(songid) - length)**2

        # check title length
        titlescore = abs(
            len(title) -
            len(library[songid]['artist'] + library[songid]['title']))

        if lenscore + titlescore > _MATCHTHRESH:
            continue

        matches2.append((lenscore+titlescore, songid))

    matches2 = sorted(matches2)

    if False:
        print "Matches for %s (%d):" % (title, length)

        def _t(sid):
            return u'{artist} / {album} / {title}'.format(**library[sid])

        for score, sid in matches2:
            print "   %s (%d) = %d" % (_t(sid), _l(sid), score)

        print ""

    if matches2:
        return library[matches2[0][1]]
    else:
        return None

def findAABestMatch(song, mc):
    #print 'Searching for "%s"...\n  ' % song
    res = mc.search_all_access(song)
    #pprint(res['song_hits'][0])
    #print '\n  '.join(' / '.join(x['track'][f] for f in ('artist', 'album', 'title')) for x in res['song_hits'])
    if res['song_hits']:
        return res['song_hits'][0]['track']
    else:
        return None



if len(sys.argv) != 2:
    print 'Usage: build_playlist.py playlist.m3u'
    sys.exit(1)

playlist = loadM3U(sys.argv[1])
client = getClient()

print "Found %d songs:" % len(playlist)
for song in playlist:
    print "  %s" % song[1]

# get a playlist
gplaylist = getGMusicPlaylist(client)

library, index = getGLibrary(client)

matches = []
missing = []
for song in playlist:
    match = findLockerBestMatch(song, library, index)
    if match is not None:
        match['source'] = 'Library'
        matches.append((song[1], match))
    else:
        match = findAABestMatch(song[1], client)
        if match is not None:
            match['source'] = 'All Access'
            matches.append((song[1], match))
        else:
            missing.append(song[1])

print 'Matched %d songs:' % len(matches)
print '\n'.join(
    '  %s -> %s / %s / %s (%s)' % (
        title, gsong['title'], gsong['album'],
        gsong['title'], gsong['source']) for
    title, gsong in matches)

print 'Missing %d songs:' % len(missing)
print '\n'.join('  %s' % x for x in missing)

added = client.add_songs_to_playlist(gplaylist, ['id' in x and x['id'] or x['nid'] for _, x in matches])
print "%d songs added to playlist!" % len(added)
