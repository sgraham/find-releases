# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import cPickle
import os
import pprint
import re
import subprocess
import sys


IS_WIN = sys.platform.startswith('win32')


def Git(*args):
  args = ('git',) + args
  return subprocess.check_output(args, shell=IS_WIN)


def VersionPredicate(release_str):
  parts = release_str.split('.')
  return (int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3]))


def main():
  try:
    with open('cache.pickle', 'rb') as f:
      cache = cPickle.load(f)
  except:
    cache = {}
  cache.setdefault('tag_to_sha1', {})
  cache.setdefault('release_sha1s', {})

  prev_tag_to_sha1 = cache['tag_to_sha1']
  new_tag_to_sha1 = {}
  for tag in Git('show-ref', '--tags').splitlines():
    sha1, long_tag_name = tag.split()
    prefix = 'refs/tags/'
    if not long_tag_name.startswith(prefix):
      print 'ignoring', long_tag_name
      continue
    release = long_tag_name[len(prefix):]
    if not re.match(r'\d+\.\d+\.\d+\.\d+', release):
      print 'skipping non-releasey', release
      continue
    new_tag_to_sha1[release] = sha1

  new_tags = set(new_tag_to_sha1.keys())
  prev_tags = set(prev_tag_to_sha1.keys())
  intersect = new_tags.intersection(prev_tags)
  changed_tags = set(o for o in intersect
                     if prev_tag_to_sha1[o] != new_tag_to_sha1[o])
  new_tags = new_tags - intersect
  print (len(changed_tags) + len(new_tags)), "tags to update..."

  cache['tag_to_sha1'] = new_tag_to_sha1

  ordered_releases = sorted(new_tag_to_sha1.keys(), key=VersionPredicate)

  release_sha1s = cache['release_sha1s']
  caret_prefix = '^^^^' if IS_WIN else '^'
  for i in range(len(ordered_releases) - 1):
    tag = ordered_releases[i+1]
    if tag in changed_tags or tag in new_tags:
      print '\r' + tag,
      sha1s = Git('log', caret_prefix + ordered_releases[i],
                  ordered_releases[i+1], '--format=%H').split('\n')
      release_sha1s[tag] = sha1s
  cache['release_sha1s'] = release_sha1s

  try:
    with open('cache.pickle', 'wb') as f:
      cPickle.dump(cache, f)
  except Exception as e:
    print >>sys.stderr, 'Failed to save cache', e

  return 0


if __name__ == '__main__':
  sys.exit(main())
