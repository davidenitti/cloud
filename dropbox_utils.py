# -*- coding: utf-8 -*-
"""
Created on Wed Mar  4 06:31:48 2020

@author: hdatta
"""

import dropbox
import os
import shutil


# Find folder ID
def get_folders(dbx, folder):
    result = dbx.files_list_folder(folder, recursive=True)

    folders = []

    def process_dirs(entries):
        for entry in entries:
            if isinstance(entry, dropbox.files.FolderMetadata):
                folders.append(entry.path_lower + '--> ' + entry.id)

    process_dirs(result.entries)

    while result.has_more:
        result = dbx.files_list_folder_continue(result.cursor)
        process_dirs(result.entries)

    return (folders)


def wipe_dir(download_dir):
    # wipe download dir
    shutil.rmtree(download_dir)


def recursive_download(dbx, local_folder, dropbox_folder):
    # assert (folder_id.startswith('id:'))
    result = dbx.files_list_folder(dropbox_folder, recursive=True)
    folder_id = result.entries[0].id
    # determine highest common directory
    assert (result.entries[0].id == folder_id)
    common_dir = result.entries[0].path_display
    #local_folder = os.path.join(local_folder, os.path.basename(common_dir))
    file_list = []

    def process_entries(entries):
        for entry in entries:
            if isinstance(entry, dropbox.files.FileMetadata):
                file_list.append(entry)

    process_entries(result.entries)

    while result.has_more:
        result = dbx.files_list_folder_continue(result.cursor)

        process_entries(result.entries)
    exclude = ['.git', '.idea', '__pycache__', '.pytest_cache', '.pyc']
    print('Downloading ' + str(len(file_list)) + ' files...')
    i = 0
    for fn in file_list:
        skip = False
        for e in exclude:
            if e in fn.path_display:
                skip = True
                continue
        if skip:
            continue
        i += 1
        printProgressBar(i, len(file_list))
        path = local_folder + remove_prefix(fn.path_display, common_dir)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        print(path, fn.path_display)
        dbx.files_download_to_file(path, fn.path_lower)


# auxilary function to print iterations progress (from https://stackoverflow.com/questions/3173320/text-progress-bar-in-the-console)
def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end='\r')
    # Print New Line on Complete
    if iteration == total:
        print()


# inspired by https://stackoverflow.com/questions/16891340/remove-a-prefix-from-a-string and
# https://stackoverflow.com/questions/1038824/how-do-i-remove-a-substring-from-the-end-of-a-string-in-python

def remove_prefix(text, prefix):
    return text[text.lower().startswith(prefix.lower()) and len(prefix.lower()):]


def remove_suffix(text, suffix):
    return text[:-(text.endswith(suffix) and len(suffix))]
