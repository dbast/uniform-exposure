# Develop a bunch of raw pics so they look pretty much equally exposed.
# Copyright (2013) a1ex. License: GPL.

# Requires python, dcraw, ufraw, enfuse and ImageMagick.

# Usage:
# 1) Place your raw photos under a "raw" subdirectory; for example:
#  
#     $ ls -R
#          .:
#          uniform-exposure.py
#
#          ./raw:
#          IMG_0001.CR2  IMG_0002.CR2 ...
#
# 2) run the script
#
#     $ python uniform-exposure.py
#
#          IMG_0001.CR2:
#             midtones: brightness level  2160 => exposure +4.14 EV
#           highlights: brightness level 58877 => exposure +3.21,+2.28,+1.36,+0.43,-0.50 EV 
#              shadows: brightness level   289 => exposure +2.79 EV (skipping)
#           . . . .
#          Developing images... [5% done, ETA 0:05:02]...
#
# 3) the images will be placed in a directory called 'jpg'.
#
# 4) you will also get images optimized for highlights, for midtones and for shadows.

from __future__ import division

# User adjustable parameters 
# =====================================================================================

# exposure compensation, in EV
overall_bias = 0

# from 0 to 65535
highlight_level = 20000
midtone_level = 10000
shadow_level = 1000

raw_dir = 'raw'
out_dir = 'jpg'
tmp_dir = 'tmp'

ufraw_options = "--temperature=5500 --green=1 "

# for Samyang 8mm on full-frame cameras: don't analyze the black borders
samyang8ff = False

# develop full size (turn off for higher speed)
fullsize = False

def override_settings(fname, num):
    global ufraw_options, default_ufraw_options, overall_bias, default_overall_bias, highlight_level, default_highlight_level, midtone_level, default_midtone_level, shadow_level, default_shadow_level, samyang8ff, default_samyang8ff, fullsize, default_fullsize
    try:    ufraw_options = default_ufraw_options; overall_bias = default_overall_bias; highlight_level = default_highlight_level; midtone_level = default_midtone_level; shadow_level = default_shadow_level; samyang8ff = default_samyang8ff; fullsize = default_fullsize;
    except: default_ufraw_options = ufraw_options; default_overall_bias = overall_bias; default_highlight_level = highlight_level; default_midtone_level = midtone_level; default_shadow_level = shadow_level; default_samyang8ff = samyang8ff; default_fullsize = fullsize;

    # hack: ufraw renders CR2 brighter by 1 stop, compared to DNG (no idea why)
    if fname.endswith(".DNG"):
        overall_bias += 1

    # override per-picture settings here
    # for example:
    #
    # if num in range(1234, 1251):
    #       overall_bias += 2
    

# =====================================================================================

import os, sys, re, time, datetime, subprocess, shlex
from math import *
log2 = lambda x: log(x) / log(2)
sign = lambda x: x / abs(x) if x != 0 else 0

direrr = False

try: os.mkdir(out_dir)
except: print "Warning: could not create output dir '%s'" % out_dir

try: os.mkdir(tmp_dir)
except: print "Warning: could not create working dir '%s'" % tmp_dir

def progress(x, interval=1):
    global _progress_first_time, _progress_last_time, _progress_message, _progress_interval
    
    try:
        p = float(x)
        init = False
    except:
        init = True
        
    if init:
        _progress_message = x
        _progress_last_time = time.time()
        _progress_first_time = time.time()
        _progress_interval = interval
    elif x:
        if time.time() - _progress_last_time > _progress_interval:
            print >> sys.stderr, "%s [%d%% done, ETA %s]..." % (_progress_message, int(100*p), datetime.timedelta(seconds = round((1-p)/p*(time.time()-_progress_first_time))))
            _progress_last_time = time.time()


def change_ext(file, newext):
    return os.path.splitext(file)[0] + newext

def file_number(f):
    nr = re.search("([0-9][0-9][0-9][0-9]+)", j)
    if nr:
        nr = int(nr.groups()[0])
        return nr

def get_raw_data_for_median(file):
    cmd1 = "dcraw -c -h -4 '%s'" % file
    cmd2 = "convert - -type Grayscale -gravity Center %s -scale 500x500 -format %%c histogram:info:-" % ("-crop 67%x67%" if samyang8ff else "")

    if 0: # use this to troubleshoot the dcraw conversion
        cmd_dbg = cmd1 + " | convert - -type Grayscale -gravity Center -scale 500x500 " + change_ext(file, "-debug.jpg")
        print cmd_dbg
        os.system(cmd_dbg)
    
    p1 = subprocess.Popen(shlex.split(cmd1), stdout=subprocess.PIPE)
    p2 = subprocess.Popen(shlex.split(cmd2), stdin=p1.stdout, stdout=subprocess.PIPE)
    lines = p2.communicate()[0].split("\n")
    X = []
    for l in lines[1:]:
        p1 = l.find("(")
        if p1 > 0:
            p2 = l.find(",", p1)
            level = int(l[p1+1:p2])
            count = int(l[:p1-2])
            X.append((level, count))
    return X

def get_percentiles(file, percentiles):
    X = get_raw_data_for_median(file)
    
    ans = []
    for percentile in percentiles:
    
        total = sum([count for level, count in X])
        target = total * percentile / 100
        
        acc = 0
        for level, count in X:
            acc += count
            if acc >= target:
                ans.append(level)
                break

    # see where these percentile levels fall on the image
    # (where exactly it meters to keep the exposure constant)
    if 0:
        level_min = min(ans)
        level_max = max(ans)
        cmd1 = "dcraw -c -h -4 '%s'" % file
        cmd_dbg = cmd1 + " | convert - -type Grayscale -gravity Center -level %s,%s -solarize 65534 -threshold 0 '%s' " % (level_min-1, level_max+1, change_ext(file, "-test.jpg"))
        print cmd_dbg
        os.system(cmd_dbg)

    return ans

def get_medians(file):
    return get_percentiles(file, [50, 99.99, 5])

def frange(x, y, jump):
    if jump > 0:
        while x < y:
            yield x
            x += jump
    else:
        while x > y:
            yield x
            x += jump
    

def expo_range(start, end, step):
    step = abs(step) * sign(end-start)
    r = list(frange(start, end+0.5*sign(step), step))
    if len(r) <= 1:
        return [end]
    step = float(end-start) / (len(r)-1)
    r = list(frange(start, end+0.5*sign(step), step))
    return r[1:]

files = sorted(os.listdir(raw_dir))

# prefer the DNG if there are two files with the same name
for f in [f for f in files]:
    dng = change_ext(f, ".DNG")
    if f[0] == ".":
        files.remove(f)
        continue
    if dng != f and dng in files:
        files.remove(f)
        continue
    
    # only process CR2 and DNG
    if not(f.endswith(".CR2") or f.endswith(".cr2") or f.endswith(".DNG") or f.endswith(".dng")):
        files.remove(f)
        continue

progress("")
for k,f in enumerate(files):
    r  = os.path.join(raw_dir, f)
    j  = os.path.join(out_dir, change_ext(f, ".jpg"))
    jm = os.path.join(tmp_dir, change_ext(f, "-m.jpg"))
    jh = os.path.join(tmp_dir, change_ext(f, "-h.jpg"))
    js = os.path.join(tmp_dir, change_ext(f, "-s.jpg"))
    ufr = change_ext(r, ".ufraw")

    # don't overwrite existing jpeg files
    if os.path.isfile(j) or os.path.isfile(change_ext(j, "r.jpg")):
        print "%s: output file %s already exists, skipping" % (r, j)
        continue

    # skip sub-dirs under raw_dir
    if not os.path.isfile(r):
        continue
    
    if f.lower().endswith('.jpg'):
        continue
    
    print ""
    print "%s:" % r

    # override settings
    override_settings(r, file_number(r))
    print ufraw_options

    # compute percentiles
    mm, mh, ms = get_medians(r)

    # normal exposure
    ecm = -log2(mm / midtone_level) + overall_bias

    # exposure for highlights
    ech = max(-log2(mh / highlight_level) + overall_bias, -0.5)
    needs_highlight_recovery = (ech < ecm - 0.5);

    # exposure for shadows
    ecs = -log2(ms / shadow_level) + overall_bias
    needs_shadow_recovery = (ecs > ecm + 0.5)

    # compensate normal exposure to avoid brightness changes when doing strong recovery (approximate)
    if needs_highlight_recovery: ecm += 0.25 * abs(ech - ecm)
    if needs_shadow_recovery: ecm -= 0.25 * abs(ecs - ecm)

    # do highlight/shadow recovery in more steps, not just one
    if needs_highlight_recovery: ech = expo_range(ecm, ech, 1)
    else: ech = [ech]
    if needs_shadow_recovery: ecs = expo_range(ecm, ecs, 1)
    else: ecs = [ecs]

    # print the levels
    print "    midtones: brightness level %5d => exposure %+.2f EV" % (mm, ecm)
    print "  highlights: brightness level %5d => exposure %s EV %s" % (mh, ",".join(["%+.2f" % e for e in ech]), "" if needs_highlight_recovery else "(skipping)")
    print "     shadows: brightness level %5d => exposure %s EV %s" % (ms, ",".join(["%+.2f" % e for e in ecs]), "" if needs_shadow_recovery else "(skipping)")
    print "", ; sys.stdout.flush()

    # any ufraw settings file? use it when developing
    if os.path.isfile(ufr):
        r = ufr

    # develop the raws
    shrink = 1 if fullsize == True else (2 if fullsize == False else fullsize)
    jpegs = [jm]
    print "(midtones)", ; sys.stdout.flush()
    cmd = "ufraw-batch --out-type=jpg --overwrite %s --exposure=%s '%s' --output='%s' --clip=film --shrink=%d 2>> dev.log" % (ufraw_options, ecm, r, jm, shrink)
    os.system(cmd)
    
    if needs_highlight_recovery:
        # highlight recovery
        print "(highlights", ; sys.stdout.flush()
        for ji,e in enumerate(ech):
            if ji > 0: print "\b.", ; sys.stdout.flush()
            jp = change_ext(jh, "%d.jpg" % ji)
            cmd = "ufraw-batch --out-type=jpg --overwrite %s --exposure=%s '%s' --output='%s' --clip=film --shrink=%d 2>> dev.log" % (ufraw_options, e, r, jp, shrink)
            os.system(cmd)
            jpegs.append(jp)
        print "\b)", ; sys.stdout.flush()

    if needs_shadow_recovery:
        # shadow recovery
        print "(shadows", ; sys.stdout.flush()
        for ji,e in enumerate(ecs):
            if ji > 0: print "\b.", ; sys.stdout.flush()
            jp = change_ext(js, "%d.jpg" % ji)
            cmd = "ufraw-batch --out-type=jpg --overwrite %s --exposure=%s '%s' --output='%s' --clip=film --shrink=%d 2>> dev.log" % (ufraw_options, e, r, jp, shrink)
            os.system(cmd)
            jpegs.append(jp)
        print "\b)", ; sys.stdout.flush()

    if needs_highlight_recovery or needs_shadow_recovery:
        # blend highlights and shadows
        print "(enfuse)", ; sys.stdout.flush()
        cmd = "enfuse %s --gray-projector=value --saturation-weight=0 --exposure-sigma=0.3 -o '%s' 2>> dev.log" % (" ".join(["'%s'" % ji for ji in jpegs]), j)
        os.system(cmd)
    else:
        # nothing to blend
        print "(copy)", ; sys.stdout.flush()
        cmd = "cp '%s' '%s'" % (jm, j)
        os.system(cmd)
    
    cmd = "echo \"%s: overall_bias=%g; highlight_level=%g; midtone_level=%g; shadow_level=%g; ufraw_options='%s'; \" >> settings.log" % (f, overall_bias, highlight_level, midtone_level, shadow_level, ufraw_options)
    os.system(cmd)

    if 0:
        # lossless optimization of the Huffman tables
        cmd = "jpegoptim '%s'" % j
        os.system(cmd)
        
        # copy over exif-data (without old preview/thumbnail-images and without orientation as ufraw already takes care of it) and add comment with processing parameters
        comment = "overall_bias=%g; highlight_level=%g; midtone_level=%g; shadow_level=%g; ufraw_options='%s'; " % (overall_bias, highlight_level, midtone_level, shadow_level, ufraw_options)
        comment += "midtones: brightness level %5d => exposure %+.2f EV; " % (mm, ecm)
        comment += "highlights: brightness level %5d => exposure %s EV %s; " % (mh, ",".join(["%+.2f" % e for e in ech]), "" if needs_highlight_recovery else "(skipping)")
        comment += "shadows: brightness level %5d => exposure %s EV %s" % (ms, ",".join(["%+.2f" % e for e in ecs]), "" if needs_shadow_recovery else "(skipping)")
        cmd = "exiftool -TagsFromFile '%s' -comment=%s -ThumbnailImage= -PreviewImage= -Orientation= -z -overwrite_original '%s'" % (r, '"%s"' % comment, j)
        os.system(cmd)

    print ""
    progress((k+1) / len(files))


