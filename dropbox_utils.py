from __future__ import print_function
import dropbox
import os
import datetime, time


def list_folder(dbx, folder):
    """List a folder.

    Return a dict mapping unicode filenames to
    FileMetadata|FolderMetadata entries.
    """
    path = '/%s' % (folder)
    while '//' in path:
        path = path.replace('//', '/')
    path = path.rstrip('/')
    try:
        res = dbx.files_list_folder(path)
    except dropbox.exceptions.ApiError as err:
        print('Folder listing failed for', path, '-- assumed empty:', err)
        return None
    else:
        rv = {}
        for entry in res.entries:
            rv[entry.name] = entry
        return rv


def upload2(dbx, file_path, dropbox_path, overwrite=True):
    while '//' in dropbox_path:
        dropbox_path = dropbox_path.replace('//', '/')
    mode = (dropbox.files.WriteMode.overwrite
            if overwrite
            else dropbox.files.WriteMode.add)
    f = open(file_path, 'rb')
    file_size = os.path.getsize(file_path)

    CHUNK_SIZE = 4 * 1024 * 1024

    if file_size <= CHUNK_SIZE:
        print(dbx.files_upload(f.read(), dropbox_path, mode, mute=True))
    else:
        upload_session_start_result = dbx.files_upload_session_start(f.read(CHUNK_SIZE))
        cursor = dropbox.files.UploadSessionCursor(session_id=upload_session_start_result.session_id,
                                                   offset=f.tell())
        commit = dropbox.files.CommitInfo(path=dropbox_path, mode=mode)
        i = 0
        while f.tell() < file_size:
            i += 1
            if i % 30 == 0:
                print("upload {} {}%".format(file_path, 100 * f.tell() // file_size))
            if ((file_size - f.tell()) <= CHUNK_SIZE):
                print(dbx.files_upload_session_finish(f.read(CHUNK_SIZE),
                                                      cursor,
                                                      commit))
            else:
                dbx.files_upload_session_append(f.read(CHUNK_SIZE),
                                                cursor.session_id,
                                                cursor.offset)
                cursor.offset = f.tell()

    f.close()


def upload(dbx, local_path, dropbox_path, overwrite=True):
    """Upload a file.

    Return the request response, or None in case of error.
    """
    while '//' in dropbox_path:
        dropbox_path = dropbox_path.replace('//', '/')
    mode = (dropbox.files.WriteMode.overwrite
            if overwrite
            else dropbox.files.WriteMode.add)
    mtime = os.path.getmtime(local_path)
    with open(local_path, 'rb') as f:
        data = f.read()
    try:
        res = dbx.files_upload(
            data, dropbox_path, mode,
            client_modified=datetime.datetime(*time.gmtime(mtime)[:6]),
            mute=True)
    except dropbox.exceptions.ApiError as err:
        print('*** API error', err)
        return None
    print('uploaded as', res.name.encode('utf8'))
    return res


def recursive_download(dbx, local_folder, dropbox_folder, print_info=False):
    if not os.path.exists(local_folder):
        os.makedirs(local_folder)
    exclude = ['.git', '.idea', '__pycache__','.pytest_cache','autoencoders','Sampling']
    res = list_folder(dbx, dropbox_folder)
    if res is None:
        return
    print('downloading', local_folder, dropbox_folder)
    for f in res:
        local_path_file = os.path.join(local_folder, f)
        dropbox_path_file = os.path.join(dropbox_folder, f)
        if f not in exclude:
            # print(dropbox_path_file,local_path_file)
            if isinstance(res[f], dropbox.files.FolderMetadata):
                recursive_download(dbx, local_path_file, dropbox_path_file)
            else:
                md = res[f]
                to_download = False
                if os.path.exists(local_path_file):
                    mtime = os.path.getmtime(local_path_file)
                    mtime_dt = datetime.datetime(*time.gmtime(mtime)[:6])
                    size = os.path.getsize(local_path_file)
                    if (isinstance(md, dropbox.files.FileMetadata) and
                            mtime_dt == md.client_modified and size == md.size):  # fixme always different
                        print(dropbox_path_file, 'is already synced [stats match]')
                    else:
                        # print(mtime_dt,md.client_modified,size,md.size)
                        # print(dropbox_path_file, 'exists with different stats, downloading')
                        to_download = True
                else:
                    # print(dropbox_path_file, 'does not exists, downloading')
                    to_download = True
                if to_download:
                    if print_info:
                        print('downloading', dropbox_path_file, 'to', local_path_file)
                    dbx.files_download_to_file(local_path_file, dropbox_path_file)


def recursive_upload(dbx, local_folder, dropbox_folder, print_info=False):
    res = list_folder(dbx, dropbox_folder)
    if res is None:
        print('creating', dropbox_folder)
        dbx.files_create_folder(dropbox_folder)
    exclude = ['.git', '.idea', '__pycache__']
    res = os.listdir(local_folder)
    dropbox_list = list_folder(dbx, dropbox_folder)
    print('uploading', local_folder, dropbox_folder)
    for f in res:
        local_path_file = os.path.join(local_folder, f)
        dropbox_path_file = os.path.join(dropbox_folder, f)
        if f not in exclude:
            # print(dropbox_path_file,local_path_file)
            if not os.path.isfile(local_path_file):
                recursive_upload(dbx, local_path_file, dropbox_path_file)
            else:
                to_upload = False
                if f in dropbox_list:
                    md = dropbox_list[f]
                    mtime = os.path.getmtime(local_path_file)
                    mtime_dt = datetime.datetime(*time.gmtime(mtime)[:6])
                    size = os.path.getsize(local_path_file)
                    if (isinstance(md, dropbox.files.FileMetadata) and
                            mtime_dt == md.client_modified and size == md.size):  # fixme always different
                        print(dropbox_path_file, 'is already synced [stats match]')
                    else:
                        # print(mtime_dt,md.client_modified,size,md.size)
                        # print(dropbox_path_file, 'exists with different stats, uploading')
                        to_upload = True
                else:
                    # print(dropbox_path_file, 'does not exists, uploading')
                    to_upload = True
                if to_upload:
                    if print_info:
                        print('uploading', local_path_file, 'to', dropbox_path_file)
                    upload2(dbx, local_path_file, dropbox_path_file)
