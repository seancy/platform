#!/bin/bash
"""
This script is used to automatically extract our platform's strings which need to be translated. And merge with our existing translated languages.
The process is below.
1. Extracts plaftorm's latest strings needed to be translated.
2. Concatenates and merges the specified PO files, which are django-partial.po, django-studio.po(including xblock)...
3. Merges with existing specific language, update the specific language files.
4. Concatenates and merges client's themes.
5. Compiles PO files to MO files.
6. Compiles PO files to djangojs.js files(Note: make sure that lms and cms are both compiled).
"""

import os
import subprocess
import sys

DEFAULT_LANG = "en"
PLAT_PATH = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXTRACT_CMD = ["paver", "i18n_extract"]
COMPILE_JS_CMD = [[
    "python", "manage.py", "lms", "--settings=devstack_docker", "compilejsi18n"
], [
    "python", "manage.py", "cms", "--settings=devstack_docker", "compilejsi18n"
]]
PARTIAL_PO = [
    "django-partial.po", "django-studio.po", "mako-studio.po", "mako.po",
    "wiki.po", "xblocks.po"
]
PARTIAL_JS_PO = [
    "djangojs-partial.po", "djangojs-studio.po", "underscore.po",
    "underscore-studio.po", "xblocksjs.po"
]
DJANGO_PO = "django.po"
DJANGO_JS_PO = "djangojs.po"
DJANGO_MO = "django.mo"
DJANGO_JS_MO = "djangojs.mo"
CUSTOMERS_EXTRA_PO = "customers-extra.po"
LANGUAGES = ["ar", "es_419", "fr", "he", "hi", "ko_KR", "pt_BR", "ru", "zh_CN"]


def execute_cmd(cmd, shell=False):
    """Execute subprocess command(shell command).
    Args:
        cmd: string or a sequence of program arguments.
        shell: If using shell to  execute command.
    """
    try:
        print "Starts executing \"{}\"".format(" ".join(cmd))
        retcode = subprocess.call(cmd, shell=shell)
        if retcode < 0:
            print >> sys.stderr, "Child process was terminated by signal", -retcode
        else:
            print >> sys.stderr, "Child process returned", retcode
    except OSError as e:
        print >> sys.stderr, "Execution failed:", e


def extract(extract_cmd):
    """Extracts platform's latest string needed to be translated.
    Using 'paver i18n_extract' command(in plaform code) to extract different part po files. Located in conf/local/en/LC_MESSAGES.
    """
    execute_cmd(extract_cmd)


def msg_merge(def_po, ref_pot, update=False):
    """Merges two Uniforum style .po files together.
    The def.po file is an existing PO file with translations which will be
    taken over to the newly created file as long as they still match; comments will be preserved, but extracted comments and file positions will be discarded. The ref.pot file is the last created PO file with up-to-date source references but old translations, or a PO Template file (generally created by xgettext); any translations or comments in the file will be  discarded, however dot comments and file positions will be preserved.  Where an exact match cannot be found, fuzzy matching is used to produce better results.
    """
    cmd = ["msgmerge", "-U", def_po, ref_pot
           ] if update else ["msgmerge", def_po, ref_pot]
    execute_cmd(cmd)


def msg_cat(output, partials, use_first=False):
    """Concatenates different partails into a single PO file."""
    for part in partials:
        if not os.path.isfile(part):
            print "{} is invaild file name, will be skipped".format(part)
    partials = [part for part in partials if os.path.isfile(part)]
    cmd = ["msgcat", "--use-first", "-o", output
           ] + partials if use_first else ["msgcat", "-o", output] + partials
    execute_cmd(cmd)


def compile(pofile, mofile):
    """Compiles po files to mo files.
    """
    cmd = ["msgfmt", "-o", mofile, pofile]
    execute_cmd(cmd)


def compilejs(cmds):
    """Compiles po files to djangjs.js files.
    """
    for cmd in cmds:
        execute_cmd(cmd)


def file_path(filename, lang="en"):
    """Finds specific file name's path according specific language.
    """
    return os.path.join(PLAT_PATH,
                        "conf/locale/{}/LC_MESSAGES/{}".format(lang, filename))


def init_trans():
    """Does init work, extracts and cat deafult en po files
    """
    try:
        os.chdir(PLAT_PATH)
    except OSError as e:
        print "%s is invalid path" % PLAT_PATH
    extract(EXTRACT_CMD)
    partial_paths = [file_path(part) for part in PARTIAL_PO]
    partialjs_paths = [file_path(part) for part in PARTIAL_JS_PO]
    msg_cat(file_path(DJANGO_PO), partial_paths)
    msg_cat(file_path(DJANGO_JS_PO), partialjs_paths)


def trans_lang(lang):
    # Merges reference po file(en) with target po file(fr, zn_CH...).
    msg_merge(file_path(DJANGO_PO, lang), file_path(DJANGO_PO), update=True)
    msg_merge(file_path(DJANGO_JS_PO, lang),
              file_path(DJANGO_JS_PO),
              update=True)
    # Appends customer po files.
    customer_file = file_path(CUSTOMERS_EXTRA_PO, lang)
    if os.path.isfile(customer_file):
        msg_cat(file_path(DJANGO_PO, lang), [customer_file], use_first=True)
    # Compiles po files to mo files.
    compile(file_path(DJANGO_PO, lang), file_path(DJANGO_MO, lang))
    compile(file_path(DJANGO_JS_PO, lang), file_path(DJANGO_JS_MO, lang))
    # Updates djangojs.js file.
    compilejs(COMPILE_JS_CMD)


def main():
    if len(sys.argv) < 2:
        print "need extra args for specific languages(e.g. fr zh_CN)"
        sys.exit(1)
    init_trans()
    for lang in sys.argv[1:]:
        if lang not in LANGUAGES:
            print "invalid language, skip {}.".format(lang)
            continue
        print "Starts translating {}...".format(lang)
        trans_lang(lang)


if __name__ == "__main__":
    main()
