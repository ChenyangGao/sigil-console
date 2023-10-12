# Sigil BookContainer API

Excerpt from this [document](https://fossies.org/linux/Sigil/docs/Sigil_Plugin_Framework_rev14.epub#sigil_python_plugins.html#sigil_toc_id_1).

See `BookContainer` source code [here](https://github.com/Sigil-Ebook/Sigil/blob/master/src/Resource_Files/plugin_launchers/python/bookcontainer.py).

More docs:
  - [https://fossies.org/linux/docs/](https://fossies.org/linux/docs/)
  - [https://github.com/Sigil-Ebook/Sigil/tree/master/docs](https://github.com/Sigil-Ebook/Sigil/tree/master/docs)

## The Edit Plugin Interface: bookcontainer.py

Each `"edit"` plugin is passed an instance of BookContainer Class (bk) as the single parameter to their run() function. The BookContainer class effectively implements the Python 3.4 edit plugin interface for Sigil. All of the plugin interface code has been written to run on python 3.4 or later systems. For more information, see [the Anatomy of a Plugin](https://fossies.org/linux/Sigil/Text/sigil_plugin_anatomy.html) . The BookContainer class contains a number of interface routines, utilities, and iterators to allow you safe access to the ePub ebook internals currently being edited by Sigil (in the current active window).

The primary idea behind the interface is that it will parse the OPF file for you behind the scenes and make available files via their manifest ids. As users add and remove files, change metadata, etc, the underlying OPF file is automatically updated to reflect those changes. If your code requires you to parse the OPF file yourself, the currently updated OPF file contents can be generated and returned as a data string.

In addition to the interface provided via the book container class, the following site packages are also available to Python 3.4 or later interpreter engines for plugin developers to take advantage of:

1. Sigil Customized Version of BeautifulSoup4 called sigil_bs4
2. Sigil custom interface to Google's Gumbo (html5) Parser
3. Pillow (PIL) for Image Manipulation
4. regex enhanced regular expressions
5. html5lib a pure python html5 parser
6. lxml an elementree interface to libxml2 for XML and html processing
7. css-parser a collection of routines to help process css files
8. cssselect routine to select elements in lxml tree using css selection rules
9. chardet routines to detect encoding used in strings
10. six module to allow other modules to run on Python 3.4
11. tk/tcl Tkinter widget kit for creating a graphical user interface for your plugin
12. PyQt5 basic widget module to allow your plugin to create a Qt graphical user interface that better matches Sigil's own

If you examine the bookcontainer.py file you will see the following definition:

```python
from __future__ import unicode_literals, division, absolute_import, print_function 
import sys 
import os 
from quickparser import QuickXHTMLParser 

class ContainerException(Exception): 
	pass 

class BookContainer(object): 
    self.qp=QuickXHTMLParser() 
  
```

The instance of the BookContainer class passed in will be referred to as *bk* in the description of the interface that follows.

The actual container source code can be found in the [Sigil github tree in src/Sigil/Resource_Files/plugin_launchers/python.](https://github.com/Sigil-Ebook/Sigil/tree/master/src/Resource_Files/plugin_launchers/python)

For ``"edit"`` plugins see [bookcontainer.py](https://fossies.org/linux/Sigil/Text/bookcontainer_py.html) , for input plugins see [inputcontainer.py](https://fossies.org/linux/Sigil/Text/inputcontainer_py.html), for output plugins see [outputcontainer.py](https://fossies.org/linux/Sigil/Text/outputcontainer_py.html), and for validation plugins see [validationcontainer.py](https://fossies.org/linux/Sigil/Text/validationcontainer_py.html).

There is a [JSONPrefs class for storing preferences settings](https://fossies.org/linux/Sigil/Text/quickparser_py.html). And a simple to use stream-based xml parser provided to users in [quickparser.py](https://fossies.org/linux/Sigil/Text/quickparser_py.html). Additional resources for developers include a [plugin interface to the Hunspell spellchecker](https://fossies.org/linux/Sigil/Text/pluginhunspell_py.html) and [an interface to Google's Gumbo html5 parser via BeautifulSoup4](https://fossies.org/linux/Sigil/Text/sigil_gumbo_bs4_adapter_py.html). There is also a [collection of epub utility routines](https://fossies.org/linux/Sigil/Text/epub_utils_py.html) provided and a [set of routines to make it easier to write code for Python 3.4](https://fossies.org/linux/Sigil/Text/compatibility_utils_py.html).

## Routines to Access and Manipulate OPF elements

### Access routines for the toc.ncx and the page-map.xml

```python
bk.gettocid()
```

- returns the current manifest id as a unicode string for the toc.ncx Table of Contents

```python
bk.getpagemapid()
```

- returns the current manifest id as a unicode string for the page-map.xml (or None)

### Routines to get/set and the spine elements

```python
bk.getspine()
```

- returns an ordered list of tuples (manifest_id, linear)
- manifest_id is a unicode string representing a specific file in the manifest
- linear is either `"yes"` or `"no"`

```python
bk.setspine(new_spine)
```

- sets the current spine order to new_spine
- where new_spine is an ordered list of tuples (manifest_id, linear)
- manifest_id is a unicode string representing a specific file
- linear is either `"yes"` or `"no"`

```python
bk.spine_insert_before(position, manifest_id_to_insert, linear, properties=None):
```

- inserts the string manifest_id_to_insert immediately before given position in the spine
- positions start numbering at 0
- position = 0 will prepend to the spine
- position = -1 or position >= spine length will append
- linear is either `"yes"` or `"no"`
- properties is None for epub2 but can have page properties for epub3

```python
bk.getspine_ppd()
```

- returns a unicode string indicating page-progression direction (`"ltr"`, `"rtl"`, None)

```python
bk.setspine_ppd(page-progression-direction)
```

- sets the spine page-progression-direction to the unicode string page-progression-direction
- allowable values are `"ltr"`, `"rtl"` or None

### Routines to get and set the guide elements

```python
bk.getguide()
```

- returns the guide as an ordered list of tuples (type, title, href)
- where type (unicode string) is the guide type
- title (unicode string) is the associated guide title
- href (unicode string) is the associated guide target uri href

```python
bk.setguide(new_guide):
```

- sets the guide to be new_guide where new_guide is an ordered list of tuples (type, title, href)
- type (unicode string) is the guide type
- title (unicode string) is the associated guide title
- href (unicode string) is the associated target uri href

### Routines to set and extract the metadata xml

```python
bk.getmetadataxml()
```

- returns a unicode string of the metadata xml fragment from the OPF

```python
bk.setmetadataxml(new_metadata)
```

- sets the OPF metadata xml fragment to be new_metadataxml
- where new_metadataxml is a unicode string wrapped in its metadata start/end tags

### Routines to set and extract the package tag from the OPF

```python
bk.getpackagetag()
```

- returns the starting package tag as a unicode string

```python
bk.setpackagetag(new_tag)
```

- sets the starting package tag to new_tag which is a unicode string

## Routines for reading / writing / adding / deleting files in the OPF manifest

```python
bk.readfile(manifest_id)
```

- returns the contents of the file with the provided manifest_id unicode string as binary data or unicode string as appropriate

```python
bk.writefile(manifest_id, data)
```

- writes the unicode text or binary data string to the file pointed to by the provided manifest_id string. If text, the file itself will be utf-8 encoded.

```python
bk.addfile(desired_unique_manifest_id, file_basename_with_extension, data, mime=None, properties=None, fallback=None, overlay=None)
```

- creates a new file and gives it the desired_unique_manifest_id string
- where basename is the desired name of the file with extension (no path added)
- data is either a string of binary data or a unicode text string
- if provided the file will be given the media-type provided by the mime-string, and if not provided the file extension is used to set the appropriate media-type
- to support epub3 manifests, properties, fallback, and media-overlay atributes can also be set.

```python
bk.deletefile(manifest_id)
```

- removes the file associated with that manifest id unicode string and removes any existing spine entries as well

## Routines for reading / writing / adding / deleting other ebook files that do not exist in the OPF manifest

```python
bk.readotherfile(book_href)
```

- returns the contents of the file pointed to by an href relative to the root directory of the ebook as unicode text or binary bytestring data

```python
bk.writeotherfile(book_href, data)
```

- writes data (binary or unicode for text) to a currently existing file pointed to by the ebook href. If text, the file itself will be utf-8 encoded

```python
bk.addotherfile(book_href, data)
```

- creates a new file with desired href (relative to the ebook root directory) with the supplied data.
- the path to the href will be automatically created
- data is a bytestring that is unicode for text and binary otherwise. If text, the resulting file itself will be utf-8 encoded

```python
bk.deleteotherfile(book_href)
```

- deletes the file pointed to by the href (relative to the ebook root directory)

## Iterators

```python
bk.text_iter():
```

- python iterator over all xhtml/html files: yields the tuple (manifest_id, OPF_href)

```python
bk.css_iter():
```

- python iterator over all style sheets (css) files: yields the tuple (manifest_id, OPF_href)

```python
bk.image_iter():
```

- python iterator over all image files: yields the tuple (manifest_id, OPF_href, media-type)

```python
bk.font_iter():
```

- python iterator over all font files: yields the tuple (manifest_id, OPF_href, media-type)

```python
bk.manifest_iter():
```

- python iterator over all files in the OPF manifest: yields the tuple (manifest_id, OPF_href, media-type)

```python
bk.spine_iter():
```

- python iterator over all files in the OPF spine in order: yields the tuple (spine_idref, linear, OPF_href)

```python
bk.guide_iter():
```

- python iterator over all entries in the OPF guide:
- yields the tuple (reference_type, title, OPF_href, manifest_id_of_OPF_ href)

```python
bk.media_iter():
```

- python iterator over all audio and video files: yields the tuple (manifest_id, OPF_href, media-type)

```python
bk.other_iter():
```

- python iterator over all files not in the Manifest: yields href from ebook root directory

```python
bk.selected_iter():
```

- python iterator over all files selectd by the user in the BookBrowser before the Plugin was launched:
- yields the tuple (id_type, id)

## Miscellaneous Routines

```python
bk.launcher_version():
```

- returns the release date of the launcher code as an integer generated as YYYYMMDD

```python
bk.epub_version():
```

- returns as a unicode string the epub version ("2.0" or "3.0") of the current epub as determined by the version attribute value on the OPF package tag

```python
bk.get_opf():
```

- returns the current OPF as a unicode string
- incorporates all of the changes preceding this call

```python
bk.copy_book_contents_to(destdir):
```

- copies all ebook contents to the previous destination directory created by the user

```python
bk.plugin_dir():
```

- returns the name of the plugin directory

```python
bk.plugin_name():
```

- returns the name of the plugin

## Convenience Routines to map manifest id to OPF_href, basename, and media-type

```python
bk.href_to_id(OPF_href, ow=None):
```

- given an OPF href, return the manifest id, if the href does not exist return ow

```python
bk.id_to_mime(manifest_id, ow=None):
```

- given a manifest id, return the media-type, if the manifest_id does not exist return ow

```python
bk.basename_to_id(basename, ow=None):
```

- given a file's basename (with extension) return its manifest id, otherwise return ow

```python
bk.id_to_href(id, ow=None):
```

- given a manifest_id return its OPF href, otherwise return ow

```python
bk.href_to_basename(href, ow=None):
```

- given an OPF_href return the basename (with extension) of the file OPF, otherwise return ow

## New ePub3 Interface Routines

```python
bk.getspine_epub3()
```

- return an ordered list of tuples (id, linear, properties)

```python
bk.setspine_epub3(new_spine)
```

- set the spine to the ordered list of tuples (id, linear, properties (or None)

```python
bk.setspine_idref_epub3_attributes(idref, linear, properties)
```

- set the spine with provided idref with linear and properties values

```python
bk.set_manifest_epub3_attributes(id, properties=None, fallback=None, overlay=None)
```

- set the epub3 manifest properties, fallback, and media-overlay attributes for this manifest id

## New ePub3 Iterators

```python
bk.manifest_epub3_iter():
```

- yields manifest id, href, media-type, properties, fallback, media-overlay

```python
bk.spine_epub3_iter():
```

- yields spine idref, linear(yes, no, None), properties, and href in spine order

## New ePub3 Convenience Mapping Routines

```python
bk.id_to_properties(id, ow=None)
```

- maps manifest id to its properties attribute

```python
bk.id_to_fallback(id, ow=None)
```

- maps manifest id to its fallback attribute

```python
bk.id_to_overlay(id, ow=None)
```

- maps manifest id to its media-overlay attribute

## New Routines for better Plugin User Interfaces

```python
sigil_ui_lang()
```

- return the current user interface language set in Sigil's Preferences

```python
sigil_spellcheck_lang()
```

- return the language the users has currently set for Spellchecking in Sigil's Preferences

## New Routines for supporting custom epub for Sigil 1.0

A book path (aka `"bookpath"` aka `"book_href"` aka `"bookhref"`) is a unique relative path from the ebook root to a specific file.

As a relative path meant to be used in an href or src `"link"`, it only uses forward slashes "/" as path separators.

Since all files exist inside the epub root (the folder the epub was unzipped into), bookpaths will NEVER have or use "./" or "../" ie they are always in canonical form.

For example under Sigil-0.9.XX all epubs were put into a standard structure. Under this standard structure book paths would look like the following:

- OEBPS/content.opf
- OEBPS/toc.ncx
- OEBPS/Text/Section0001.xhtml
- OEBPS/Images/cover.jpg
- ...

and src and hrefs always looked like the following:

- from Section0001.xhtml to Section0002.xhtml:
  ```python
  "../Text/Section0002.xhtml"
  ```

- from Section0001.xhtml to cover.jpg:
  ```python
  "../Images/cover.jpg"
  ```

- from content.opf to Section0001.xhtml:
  ```python
  "Text/Section0001.xhtml"
  ```

- from toc.ncx to Section0001.xhtml:
  ```python
  "Text/Section0001.xhtml"
  ```

Under Sigil 1.0 and later, the original epub structure will be preserved meaning that file names like "content.opf" could be named "package.opf", and be placed almost anyplace inside the epub. This is true for almost all files.

So to uniquely identify a file, you need to know either the bookpath of the OPF file itself and the manifest href to the specific file, or the path from the epub root to the file (ie. its bookpath)

Therefore the Sigil plugin interface for Sigil 1.0 and later has been extended to allow the plugin developer to more easily work with bookpaths, create links between bookpaths, etc.

We will use the terms book_href (or bookhref) interchangeably with bookpath with the following convention:

- use book_href or bookhref when working with `"other"` files outside the manifest
- use bookpath when working with files in the opf manifest
- use either when working with the OPF file as it is at the intersection

```python
bk.get_opfbookpath()
```

- returns the bookpath/book_href to the opf file

```python
bk.get_startingdir(bookpath)
```

- returns the book relative path to the folder containing this bookpath

```python
bk.build_bookpath(href, starting_dir)
```

- return a bookpath for the file pointed to by the href from the specified bookpath starting directory

```python
bk.get_relativepath(from_bookpath, to_bookpath)
```

- returns the href relative path from source bookpath to the target bookpath

```python
bk.addbookpath(uniqueid, bookpath, data, mime=None)
```

- adds a new file to the *manifest* with the stated bookpath and with the provided uniqueid, data, (and media type if specified)

```python
bk.bookpath_to_id(bookpath, ow=None)
```

- looks up the provided bookpath and returns the corresponding manifest id
- if the bookpath does not exist in the OPF manifest, ow will be returned

```python
bk.id_to_bookpath(manifest_id, ow=None)
```

- looks up the provided manifest id and returns the corresponding bookpath of the file
- if the manifest id does not exist in the OPF manifest, ow will be returned

```python
bk.group_to_folders(group, ow=None)
```

- returns a sorted list of folders for the specified file type group
- valid groups: `"Text"`, `"Styles"`, `"Images"`, `"Fonts"`, `"Audio"`, `"Video"`, `"ncx"`, `"opf"`, and `"Misc"`
- the first book relative folder path in the list will be the default folder for that file type if more than one location has been used in the epub's layout

```python
bk.mediatype_to_group(mediatype, ow=None)
```

- lookup the file type group based on a file's media type
- if the media type is not found, ow is returned

```python
bk.epub_is_standard()
```

- returns true if current epub is in Sigil's previously standard format

## New Routines in Sigil 1.9

Sigil 1.8 saw the introduction of the Sigil Automate Lists feature. To make this feature useful, as of Sigil 1.9.0, we have allowed Automate Lists to pass a single line string parameter (value) to a plugin via the new Automate command SetPluginParameter [one line parameter string].

For a plugin to know it is running under an Automate List we have extended the Sigil Plugin interface with a new call:

```python
bk.using_automate()
```

- Returns true if the plugin was launched from withing an Automate List, false otherwise.

For a plugin to retrieve the value of any passed parameter from an Automate List, we have added extended the plugin interface with the following:

```python
bk.automate_parameter()
```

- Returns a single line string as set by Automate List or the null string "" if nothing was set.

These new calls are supported by launcher_versions of 20220101 or later.
