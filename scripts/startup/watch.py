#!/usr/bin/env python
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 2)
__all__ = ['watch']

# TODO: 移动文件到其他文件夹，那么这个文件所引用的那些文件，相对位置也会改变
# TODO: created 事件时，文件不存在，则文件可能是被移动或删除，则应该注册一个回调，因为事件没有被正确处理

plugin.ensure_import('watchdog')

import logging
import posixpath
import time

from collections import defaultdict, Counter
from functools import partial
from mimetypes import guess_type
from os import makedirs, path, stat
from os.path import basename, dirname, realpath, sep
from re import compile as re_compile, Pattern
from shutil import copyfile
from tempfile import TemporaryDirectory
from types import ModuleType
from typing import overload, Final, List, Optional, Union
from urllib.parse import quote, unquote, urlparse, urlunparse

from watchdog.events import (
    FileDeletedEvent, FileCreatedEvent, FileModifiedEvent, FileSystemEventHandler
)
from watchdog.observers import Observer


bc = bc

CRE_PROT: Final[Pattern] = re_compile(r'^\w+://')
CRE_REF: Final[Pattern] = re_compile(
    r'(<[^/][^>]*?[\s:](?:href|src)=")(?P<link>[^>"]+)')
CRE_URL: Final[Pattern] = re_compile(
    r'\burl\(\s*(?:"(?P<dlink>(?:[^"]|(?<=\\)")+)"|'
    r'\'(?P<slink>(?:[^\']|(?<=\\)\')+)\'|(?P<link>[^)]+))\s*\)')
CRE_EL_STYLE: Final[Pattern] = re_compile(
    r'<style(?:\s[^>]*|)>((?s:.+?))</style>')
CRE_INLINE_STYLE: Final[Pattern] = re_compile(r'<[^/][^>]*?\sstyle="([^"]+)"')

LOGGER: Final[logging.Logger] = logging.getLogger('watch')
LOGGER.setLevel(logging.INFO)
_sh = logging.StreamHandler()
LOGGER.addHandler(_sh)
_fmt = logging.Formatter('[%(asctime)s] %(levelname)s ➜ %(message)s')
_fmt.datefmt = '%Y-%m-%d %H:%M:%S'
_sh.setFormatter(_fmt)


if path is posixpath:
    _to_syspath = _to_posixpath = lambda s: s
else:
    _to_syspath = lambda s: s.replace('/', sep)
    _to_posixpath = lambda s: s.replace(sep, '/')


try:
    def openpath(path, _func=__import__('os').startfile):
        'Open a file or directory (For Windows)'
        _func(path)
except AttributeError:
    _PLATFROM_SYSTEM = __import__('platform').system()
    if _PLATFROM_SYSTEM == 'Linux':
        def openpath(path, _func=__import__('subprocess').Popen):
            'Open a file or directory (For Linux)'
            _func(['xdg-open', path])
    elif _PLATFROM_SYSTEM == 'Darwin':
        def openpath(path, _func=__import__('subprocess').Popen):
            'Open a file or directory (For Mac OS X)'
            _func(['open', path])
    else:
        def openpath(path, _func=LOGGER.error):
            'Issue an error: can not open the path.'
            _func("Can't open the path %r" % path)
    del _PLATFROM_SYSTEM


@overload
def split(
    s: bytes, 
    sep: Optional[bytes], 
    maxsplit: int, 
    start: int
) -> List[bytes]:
    ...
@overload
def split(
    s: str, 
    sep: Optional[str], 
    maxsplit: int, 
    start: int
) -> List[str]:
    ...
def split(
    s, 
    sep=None, 
    maxsplit=-1, 
    start=0, 
):
    if start == 0:
        return s.split(sep, maxsplit)
    prefix, remain = s[:start], s[start:]
    parts = remain.split(sep, maxsplit)
    parts[0] = prefix + parts[0]
    return parts


@overload
def relative_path(
    ref_path: bytes, 
    rel_path: Union[bytes, str], 
    lib: ModuleType, 
) -> bytes:
    ...
@overload
def relative_path(
    ref_path: str, 
    rel_path: Union[bytes, str], 
    lib: ModuleType, 
) -> str:
    ...
def relative_path(
    ref_path, 
    rel_path = '.', 
    lib = path, 
):
    'Relative to the directory of `rel_path`, return the path of `file_path`.'
    curdir, pardir, sep = lib.curdir, lib.pardir, lib.sep

    if isinstance(ref_path, bytes):
        curdir, pardir, sep = curdir.encode(), pardir.encode(), sep.encode()
        if isinstance(rel_path, str):
            rel_path = rel_path.encode()
    elif isinstance(rel_path, bytes):
        rel_path = rel_path.decode()

    if not ref_path:
        return rel_path

    dir_path = lib.dirname(rel_path)
    if not dir_path or dir_path == curdir or lib.isabs(ref_path):
        return ref_path

    drive, dir_path = lib.splitdrive(dir_path)
    dir_path_isabs = bool(drive or dir_path.startswith(sep))
    dir_parts = split(dir_path, sep, start=1)
    ref_parts = ref_path.split(sep)
    try:
        for i, p in enumerate(ref_parts):
            if p == curdir:
                continue
            elif p == pardir and dir_parts[-1] != pardir:
                if dir_parts.pop() == sep:
                    raise IndexError
            else:
                dir_parts.append(p)
        result_path = lib.join(drive, *dir_parts)
        if dir_path_isabs and not result_path.startswith(sep):
            return sep + result_path
        return result_path
    except IndexError:
        if dir_path_isabs:
            raise ValueError(
                f'{ref_path} relative to {rel_path} exceeded the root directory')
        return lib.join(*ref_parts[i:])


def analyze_one(bookpath, data, mime=None):
    def gen_filtered_links(links):
        for link in links:
            link = unquote(link.partition('#')[0])
            if link in ('', '.') or CRE_PROT.match(link) is not None:
                continue
            ref_path = relative_path(link, bookpath, lib=posixpath)
            yield ref_path
    if mime is None:
        mime = guess_type(bookpath)[0]
    if mime == 'text/css':
        return Counter(gen_filtered_links(
            next(filter(None, m.groups())) 
            for m in CRE_URL.finditer(data)))
    elif mime in ('text/html', 'application/xhtml+xml'):
        return {
            'ref': Counter(gen_filtered_links(
                m['link'] 
                for m in CRE_REF.finditer(data))), 
            'inline': Counter(gen_filtered_links(
                next(filter(None, m.groups()))
                for m0 in CRE_INLINE_STYLE.finditer(data)
                for m in CRE_URL.finditer(m0[0]))), 
            'style': Counter(gen_filtered_links(
                next(filter(None, m.groups()))
                for m0 in CRE_EL_STYLE.finditer(data)
                for m in CRE_URL.finditer(m0[0]))), 
        }


def analyze(bc):
    map_path_refset = {}
    map_ref_pathset = defaultdict(set)

    for fid, href, mime in bc.manifest_iter():
        if mime not in ('text/css', 'text/html', 'application/xhtml+xml'):
            continue
        bookpath = bc.id_to_bookpath(fid)
        content = bc.readfile(fid)
        result = analyze_one(bookpath, content, mime)
        map_path_refset[bookpath] = result
        if mime == 'text/css':
            for ref_bookpath in result:
                map_ref_pathset[ref_bookpath].add(bookpath)
        elif mime in ('text/html', 'application/xhtml+xml'):
            for refset in result.values():
                for ref_bookpath in refset:
                    map_ref_pathset[ref_bookpath].add(bookpath)
    return map_path_refset, map_ref_pathset


class SigilFileEventHandler(FileSystemEventHandler):

    def __init__(self, watchdir, file_mtime=None, logger=LOGGER):
        super().__init__()
        if not watchdir.endswith(sep):
            watchdir += sep
        self.logger = logger
        self._watchdir = watchdir
        self._prefix_len = len(watchdir)
        self._opf_prefix = bc._w.opf_dir + '/'
        if file_mtime is None:
            file_mtime = {
                (p := path.join(watchdir, _to_syspath(bookpath))): 
                    stat(p).st_mtime_ns
                for bookpath in bc._w.bookpath_to_id
            }
        self._file_mtime = file_mtime
        self._map_path_refset, self._map_ref_pathset = analyze(bc)
        self._file_missing = defaultdict(list)

    def _add_bookpath_ref(self, content, bookpath, mime=None):
        if mime is None:
            mime = guess_type(bookpath)[0]
        if mime in ('text/css', 'text/html', 'application/xhtml+xml'):
            if isinstance(content, bytes):
                content = content.decode()
            result = analyze_one(bookpath, content)
            self._map_path_refset[bookpath] = result
            if mime == 'text/css':
                for ref_bookpath in result:
                    self._map_ref_pathset[ref_bookpath].add(bookpath)
            elif mime in ('text/html', 'application/xhtml+xml'):
                for refset in result.values():
                    for ref_bookpath in refset:
                        self._map_ref_pathset[ref_bookpath].add(bookpath)

    def _del_bookpath_ref(self, bookpath, mime=None):
        if mime is None:
            mime = guess_type(bookpath)[0]
        if mime == 'text/css':
            refset = self._map_path_refset.pop(bookpath, None)
            if refset:
                for ref in refset:
                    self._map_ref_pathset[ref].discard(bookpath)
        elif mime in ('text/html', 'application/xhtml+xml'):
            result = self._map_path_refset.pop(bookpath, None)
            if result:
                for refset in result.values():
                    for ref_bookpath in refset:
                        self._map_ref_pathset[ref_bookpath].discard(bookpath)

    def _update_refby_files(self, bookpath, dest_bookpath, ls_refby):
        if not ls_refby:
            return

        def rel_ref(src, ref):
            # NOTE: ca means common ancestors
            ca = posixpath.commonprefix((src, ref)).count('/')
            return '../' * (src.count('/') - ca) + '/'.join(ref.split('/')[ca:])

        def url_repl(m, refby):
            try:
                link = next(filter(None, m.groups()))
            except StopIteration:
                return m[0]

            urlparts = urlparse(link)
            link = unquote(urlparts.path)
            if link in ('', '.') or CRE_PROT.match(link) is not None:
                return m[0]

            if relative_path(link, refby, lib=posixpath) == bookpath:
                return 'url("%s")' % urlunparse(urlparts._replace(
                    path=quote(rel_ref(refby, dest_bookpath))
                ))
            else:
                return m[0]

        def ref_repl(m, refby):
            link = m['link']
            urlparts = urlparse(link)
            link = unquote(urlparts.path)
            if link in ('', '.') or CRE_PROT.match(link) is not None:
                return m[0]
            if relative_path(link, refby, lib=posixpath) == bookpath:
                return m[1] + urlunparse(urlparts._replace(
                    path=quote(rel_ref(refby, dest_bookpath))
                ))
            else:
                return m[0]

        def sub_url_in_hxml(text, refby, cre=CRE_EL_STYLE):
            ls_repl_part = []
            for match in cre.finditer(text):
                repl_part, n = CRE_URL.subn(partial(url_repl, refby=refby), match[0])
                if n > 0:
                    ls_repl_part.append((match.span(), repl_part))
            if ls_repl_part:
                text_parts = []
                last_stop = 0
                for (start, stop), repl_part in ls_repl_part:
                    text_parts.append(text[last_stop:start])
                    text_parts.append(repl_part)
                    last_stop = stop
                else:
                    text_parts.append(text[last_stop:])
                return ''.join(text_parts)
            return text

        for refby in ls_refby:
            if type(refby) is str:
                if refby == bookpath:
                    refby = dest_bookpath
                refby_srcpath = self._watchdir + _to_syspath(refby)
                try:
                    if stat(refby_srcpath).st_mtime_ns != self._file_mtime[refby_srcpath]:
                        self.logger.error(
                            'Automatic update reference %r -> %r was skipped, '
                            'because the file %r has been modified', 
                            bookpath, dest_bookpath, refby_srcpath
                        )
                        continue
                    content = open(refby_srcpath).read()
                except FileNotFoundError:
                    # NOTE: The file may have been moved or deleted
                    def callback(refby, refby_srcpath):
                        try:
                            if stat(refby_srcpath).st_mtime_ns != self._file_mtime[refby_srcpath]:
                                self.logger.error(
                                    'Automatic update reference %r -> %r was skipped, '
                                    'because the file %r has been modified', 
                                    bookpath, dest_bookpath, refby_srcpath
                                )
                                return
                            content = open(refby_srcpath).read()
                        except FileNotFoundError:
                            self.logger.error(
                                'Automatic update reference %r -> %r was skipped, '
                                'because the file %r disappeared', 
                                bookpath, dest_bookpath, refby_srcpath
                            )
                            return
                        content = CRE_URL.sub(partial(url_repl, refby=refby), content)
                        open(refby_srcpath, 'w').write(content)
                        self.on_modified(FileModifiedEvent(refby_srcpath), _keep_callbacks=True)
                    self._file_missing[refby_srcpath].append(callback)
                    continue
                content = CRE_URL.sub(partial(url_repl, refby=refby), content)
            else:
                refby, types = refby
                if refby == bookpath:
                    refby = dest_bookpath
                refby_srcpath = self._watchdir + _to_syspath(refby)
                try:
                    if stat(refby_srcpath).st_mtime_ns != self._file_mtime[refby_srcpath]:
                        self.logger.error(
                            'Automatic update reference %r -> %r was skipped, '
                            'because the file %r has been modified', 
                            bookpath, dest_bookpath, refby_srcpath
                        )
                        continue
                    content = open(refby_srcpath).read()
                except FileNotFoundError:
                    # NOTE: The file may have been moved or deleted
                    def callback(refby, refby_srcpath, types=types):
                        try:
                            if stat(refby_srcpath).st_mtime_ns != self._file_mtime[refby_srcpath]:
                                self.logger.error(
                                    'Automatic update reference %r -> %r was skipped, '
                                    'because the file %r has been modified', 
                                    bookpath, dest_bookpath, refby_srcpath
                                )
                                return
                            content = open(refby_srcpath).read()
                        except FileNotFoundError:
                            self.logger.error(
                                'Automatic update reference %r -> %r was skipped, '
                                'because the file %r disappeared', 
                                bookpath, dest_bookpath, refby_srcpath
                            )
                            return
                        for tp in types:
                            if tp == 'ref':
                                content = CRE_REF.sub(partial(ref_repl, refby=refby), content)
                            elif tp == 'inline':
                                content = sub_url_in_hxml(content, refby, CRE_INLINE_STYLE)
                            elif tp == 'style':
                                content = sub_url_in_hxml(content, refby, CRE_EL_STYLE)
                        open(refby_srcpath, 'w').write(content)
                        self.on_modified(FileModifiedEvent(refby_srcpath), _keep_callbacks=True)
                    self._file_missing[refby_srcpath].append(callback)
                    continue
                for tp in types:
                    if tp == 'ref':
                        content = CRE_REF.sub(partial(ref_repl, refby=refby), content)
                    elif tp == 'inline':
                        content = sub_url_in_hxml(content, refby, CRE_INLINE_STYLE)
                    elif tp == 'style':
                        content = sub_url_in_hxml(content, refby, CRE_EL_STYLE)
            open(refby_srcpath, 'w').write(content)
            self.on_modified(FileModifiedEvent(refby_srcpath), _keep_callbacks=True)

    def on_created(self, event):
        src_path = event.src_path
        self._file_missing.pop(src_path, None)
        if event.is_directory or basename(src_path).startswith('.'):
            return

        bookpath = _to_posixpath(src_path[self._prefix_len:])
        if bookpath in bc._w.bookpath_to_id: # file had already been created
            return

        self.logger.info("Created file: %s" % bookpath)

        try:
            mtime = stat(src_path).st_mtime_ns
            content = open(src_path, 'rb').read()
        except FileNotFoundError:
            return # TODO: The file may be deleted or moved, a callback should be registered here, then called when the modified event is triggered

        id_to_bookpath = bc._w.id_to_bookpath
        fid = id_base = basename(src_path)
        i = 0
        while fid in id_to_bookpath:
            i += 1
            fid = f'{i}_{id_base}'
        mime = guess_type(src_path)[0]
        bc.addbookpath(fid, bookpath, content, mime=mime)
        self._add_bookpath_ref(content, bookpath, mime)
        self._file_mtime[src_path] = mtime

    def on_deleted(self, event):
        src_path = event.src_path
        self._file_missing.pop(src_path, None)
        if basename(src_path).startswith('.'):
            return

        bookpath = _to_posixpath(src_path[self._prefix_len:])
        log = self.logger.info
        def delete(fid, bookpath):
            log("Deleted file: %s" % bookpath)
            try:
                mime = bc.id_to_mime(fid)
                bc.deletefile(fid)
            except:
                pass # file had already been deleted
            else:
                self._del_bookpath_ref(bookpath, mime)
                self._file_mtime.pop(src_path, None)

        if event.is_directory:
            pfx = bookpath + '/'
            for fid, pth in tuple(bc._w.id_to_bookpath.items()):
                if pth.startswith(pfx):
                    delete(fid, pth, bc.id_to_mime(fid))
            return

        fid = bc.bookpath_to_id(bookpath)
        if fid is not None:
            delete(fid, bookpath)

    def on_modified(self, event, _keep_callbacks=False):
        src_path = event.src_path
        if event.is_directory or basename(src_path).startswith('.'):
            return
        bookpath = _to_posixpath(src_path[self._prefix_len:])
        if bookpath not in bc._w.bookpath_to_id:
            return

        # NOTE: When a file is modified, two modified events will be triggered, 
        #       the first is truncation, and the second is writing.
        self.logger.info("Modified file: %s", bookpath)

        try:
            mtime = stat(src_path).st_mtime_ns
            if self._file_mtime.get(src_path) == mtime:
                return
            if not _keep_callbacks:
                self._file_missing.pop(src_path, None)
            content = open(src_path, 'rb').read()
        except FileNotFoundError:
            return # The file may be deleted or moved
        fid = bc.bookpath_to_id(bookpath)
        mime = bc.id_to_mime(fid)
        bc.writefile(fid, content)
        self._file_mtime[src_path] = mtime
        self._del_bookpath_ref(bookpath, mime)
        self._add_bookpath_ref(content, bookpath, mime)

    def on_moved(self, event):
        if event.is_directory:
            return

        src_path, dest_path = event.src_path, event.dest_path
        src_is_hidden = basename(src_path).startswith('.')
        dst_is_hidden = basename(dest_path).startswith('.')
        if src_is_hidden:
            if not dst_is_hidden:
                self.on_created(FileCreatedEvent(dest_path))
            return
        elif dst_is_hidden:
            self.on_deleted(FileDeletedEvent(src_path))
            return

        bookpath = _to_posixpath(src_path[self._prefix_len:])
        dest_bookpath = _to_posixpath(dest_path[self._prefix_len:])
        if bookpath not in bc._w.bookpath_to_id:
            return

        self.logger.info("Moved file: from %s to %s", bookpath, dest_bookpath)

        fid = bc.bookpath_to_id(bookpath)
        old_mime = bc.id_to_mime(fid)
        content = bc.readfile(fid)
        bc.deletefile(fid)
        mime = guess_type(dest_bookpath)[0]
        bc.addbookpath(fid, dest_bookpath, content, mime=mime)
        old_mtime = self._file_mtime[src_path]
        self._file_mtime[dest_path] = old_mtime

        map_path_refset, map_ref_pathset = self._map_path_refset, self._map_ref_pathset
        pathset = map_ref_pathset.get(bookpath)
        ls_refby = []
        if pathset:
            for p in pathset:
                result = map_path_refset[p]
                if type(result) is dict:
                    ls_refby.append((p, [key for key, val in result.items() if bookpath in val]))
                else:
                    ls_refby.append(p)

        result = map_path_refset.get(bookpath)
        self._del_bookpath_ref(bookpath, mime)
        if old_mime == mime and result is not None:
            map_path_refset[dest_bookpath] = result
            if mime == 'text/css':
                for ref_bookpath in result:
                    map_ref_pathset[ref_bookpath].add(dest_bookpath)
            else:
                for refset in result.values():
                    for ref_bookpath in refset:
                        map_ref_pathset[ref_bookpath].add(dest_bookpath)
        else:
            self._add_bookpath_ref(content, dest_bookpath, mime)

        if src_path in self._file_missing:
            callbacks = self._file_missing.pop(src_path)
            try:
                mtime = stat(dest_path).st_mtime_ns
            except FileNotFoundError:
                self._file_missing[dest_path] = callback
            else:
                if mtime == old_mtime:
                    for callback in callbacks:
                        callback(dest_bookpath, dest_path)
        self._update_refby_files(bookpath, dest_bookpath, ls_refby)


def watch():
    '将 epub 中的文件拷贝到一个文件夹，这个文件夹将被监测，而你在文件夹内所做的改动将会实时同步到 Sigil 中，按 <ctrl+c> 退出'
    with TemporaryDirectory() as d:
        outdir = bc._w.outdir
        ebook_root = bc._w.ebook_root
        WATCH_DIR = realpath(d)
        file_mtime = {}
        for bookpath in bc._w.bookpath_to_id:
            bookpath = _to_syspath(bookpath)
            destpath = path.join(WATCH_DIR, bookpath)
            makedirs(dirname(destpath), exist_ok=True)
            try:
                copyfile(path.join(outdir, bookpath), destpath)
            except FileNotFoundError:
                copyfile(path.join(ebook_root, bookpath), destpath)
            file_mtime[destpath] = stat(destpath).st_mtime_ns

        openpath(WATCH_DIR)

        event_handler = SigilFileEventHandler(WATCH_DIR, file_mtime)
        observer = Observer()
        observer.schedule(event_handler, WATCH_DIR, recursive=True)
        LOGGER.info('Watching directory %r', WATCH_DIR)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            LOGGER.info('Shutting down watching ...')
        finally:
            observer.stop()
            observer.join()
            LOGGER.info('Done')

