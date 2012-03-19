== WWWClient 1.0.0
== Advanced web browsing, scraping and automation
-- Author: Sebastien Pierre
-- Created:   21-Sep-2006
-- Updated:   19-Mar-2012

Python has some well-known web automation and processing tools such as
[Mechanize](http://wwwsearch.sourceforge.net/mechanize/), [Twill](http://twill.idyll.org/) and
[BeautifulSoup](http://www.crummy.com/software/BeautifulSoup/).  All provide
powerful operations to automatically browse and retrieve information from the
web.

However, we experienced limitations using Twill (which is based on Mechanize and
BeautifulSoup), notably the fact that it was difficult to *fine tune the HTTP
requests*, or when the *HTML file was broken* (and you can't imagine how many
HTML files are broken).

We decided to address these limitations by building a library that would allow
to write web clients, using a high-level programming interface, while also
allowing fine-grained control over the HTTP communication level.

WWWClient is a web browsing, scraping and automation client and library that can
easily be used using an interpreter (like 'ipython') or embedded within a
program. WWWClient offers both a high-level API and fine-grain control over
low-level HTTP and web specific elements, as well as a powerful scraping API
that lets you manipulate your HTML document using string, list and tree
operations at the same time. 

WWWClient is separated in four main modules:

 - The `wwwclient.client` module defines the abstract interface for an HTTP
   client. Two implementations are available: one using Python httplib module,
   the other using Curl Python bindings.

 - The `wwwclient.browse` module defines the high-level, browser-like interface
   that allows to easily browse a website. This includes session and cookie
   management.

 - The `www.scrape` module offers a set of objects and operations to easily
   parse and get information from an HTML or XML document. It is made to be
   versatile and very tolerant to malformed HTML.

 - The `www.forms` module offers a set of objects to represent and manipulate
   forms easily, while maintaining the most flexibility.

The forthcoming sections will present the *browsing* and *scraping* modules in
detail. For information on the rest of WWWClient, the best source is the API
documentation (included as [wwwclient-api.html] in the distribution)

Quickstart
==========

You should start by importing the `Session` object, which allows you to 
create browsing/scraping sessions.

>    from wwwclient import Session

Then start to do your queries:

>    print map(lambda _:_.text(), Session(verbose=1),get("http://ffctn.com/services").query("h4"))

Browsing
========

    The _browsing module_ (`wwwclient.browse`) is the module you will probably
    use the most often, because it allows to mimic a web browser and to post and
    retrieve web data.

    Before going in more details, it is important to understand the basic
    concepts behind HTTP and how they are reflected in the browsing API.

    One can express a conceptual model of the elements of an WWW client-server
    interaction as follows:

    - _Requests_ and _responses_ are the atomic elements of communication.
      Requests have a method, a request URL, headers and a body. Responses have
      a response code, headers and a body.

    - A _transaction_ is the sequence of messages starting with a request and
      all the related (provisional and final) responses.

    - A _session_ is a set of transaction that are "conceptually linked".
      Session cookies are the usual way to express this link in requests and
      responses.

    These concepts are respectively implemented as `Request`, `Response`,
    `Transaction` and `Session` classes within the browse module. The `Session`
    class being the highest-level object, this is the one you are the most
    likely to use.

Accessing a website
-------------------

    To access a website, you first need to create a new `Session` instance, and
    give it a URL :

    >   from wwwclient import browse
    >   session = browse.Session("www.google.com")

    Alternatively, you can create a blank session, and browse later:

    >   session = browse.Session()
    >   session.get("www.google.com")

    Once you have initiated your session, you usually call any of the following
    operations:

    -   `get()`  will send a `GET` request to the given URL
    -   `post()` wil send a `POST` request to the given URL
    -   `page()` will return you the HTML data of the current (last) page
    -   `last()` will return you the current (last) transaction

    You also have convenience method such as `url()`, `referer()`, or
    `status()`, `headers()` and `cookies()` which give you instant access to
    last transaction or session information. See the API for all the details.

    So usually, the usage pattern is as follows:

    >   session    = browse.Session("http://www.mysite.com")
    >   some_page  = session.get("some/page.html").data()
    >   ...
    >   other_page = session.get("some/other/page.html").data()
    >   ...

    Note that every time that you do a `get` or a `post`, a `Transaction`
    instance is returned. Transactions give you interesting information about
    "what happened" in the response :

    - the `newCookies()` method will tell you if cookies were set in the response
    - the `cookies()` method will return you the current cookie jar (the
      sesssion cookie merged with the new cookies)
    - the `redirect()` method will tell you if the response redirected you to
      somewhere.

    And you also have a bunch of other useful methods documented in the API.

        Note ________________________________________________________________
        You can also directly print a transaction or pass it through the `str`
        method to get its response data.

    If it important to tell that you can give `get` and `post` two parameters
    that will influence the way resulting transactions are processed :

    - The `follow` parameter tells if redirections should be followed. If not
      you will have to do manually something like :
    
      >   t = session.get("page.html",follow=False)
      >   while t.redirect(): t = session.get(t.redirect())
      
    - The `do` parameter tells if the transaction should be executed now or
      later. If the transaction is not executed, you can call the `do()`
      transaction method at any time. This allows to prepare transactions
      and execute them at will.

      # TODO: Example

    Now that you know the basics of browsing with WWWClient, let's see how to
    post data.

Posting data 
------------

    Posting data is usually the most complex thing you have to do when working
    on web automation. Because you can post data in many different ways, and
    because the server to which you post may react differently depending on what
    and how you post it, we worked hard to ensure that you have the most
    flexibility here.

    There are different ways to communicate data to an HTTP server. WWWClient
    browsing and HTTP client modules offer different ways of doing so,
    depending on the type of HTTP request you want to issue:

    1) Posting with GET and values as parameters::
       |
       >    session.get("http://www.google.com", params={"name":"value", ...)
       >    GET http://www.google.com?name=value
       |
       Here you simply give your parameter as arguments, and they are
       automatically url-encoded in the request URL.

    2) Posting with POST and values as parameters::
       |
       >    session.post("http://www.google.com", params={"name":"value", ...)
       >    POST http://www.google.com?name=value
       |
       Just as for the `GET` request, you give the parameters as arguments, and
       they get url-encoded in the request URL.

    3) Posting with POST and values as url-encoded data::
       |
       >    session.post("http://www.google.com", data={"name":"value", ...)
       >    POST http://www.google.com
       >    ...
       >    Content-Length: 10
       >    name=value
       |
       By giving your values to the `data` argument instead of the `params`
       argument, you ensure that they get url-encoded and passed as the request
       body.

    4) Posting with POST and values as form-encoded data::
       |
       >    session.post("http://www.google.com", fields={"name":"value", ...)
       >    POST http://www.google.com
       >    ...
       >    Content-Type: multipart/form-data; boundary= ...
       >    ------------fbb6cc131b52e5a980ac702bedde498032a88158$
       >    Content-Disposition: form-data; name="name"
       >    
       >    value
       >    ------------fbb6cc131b52e5a980ac702bedde498032a88158$
       >    ...
       |
       Here the given fields is directly converted as a `multipart/form-data`
       body.


    5) Posting with POST and values as custom data::
       |
       >    session.post("http://www.google.com", data="name=value")
       >    POST http://www.google.com
       >    ...
       >    Content-Length: 10
       >    name=value
       |
       You can always submit your own data manually if you prefer. In this case,
       simply give a string with the desired request body.

    6) Posting files as attachment::
        
       >    attach = session.attach(name="photo", filename="/path/to/myphoto.jpg")
       >    session.post("http://www.mysite/photo/submit", attach=attach)
        
       This enables sending a file as attachment to the given URL. This is a
       rather *low-level* functionaly, and you will most likely want to use the
       `submit()` method of session that allows you to submit data. This is the
       purpose of the next section.
    
    
    In some cases, you will want your data/arguments to be posted in a specific
    order. To do so, WWWClient offers you the `Pairs` class, which is actually
    used to internally represent headers, cookies and parameters.

    `Pairs` are simply ordered sets of (key, value) pairs. Using pairs, you can
    very easily specify an order for your elements, and then ensure that the
    requests you send are *exactly* how you want them to be.

        Note ___________________________________________________________________
        When specifying the `data` argument to `post()`, you cannot use
        the `fields` or `attach` arguments : they are exclusive.
        |
        Also, for any more detail on the arguments and/or behaviour of any of
        these functions, have a look at the `wwwclient.client` API
        documentation.


Submitting forms
----------------

    We've seen how to post data to web servers, using the session `post()`
    method. WWWClient offers in addition to that a `submit()` method that
    interfaces with the _scraping module_ to retrieve the forms description and
    prepare the data to be posted.

    To get the forms available in your current session, you can do:

    >   >>> session.forms()
    >   {'formname':<Form instance...>, 'otherform':..., ...}

    Which will return you a `dict` with form names as keys and `scrape.Form`
    instances as values. Alternatively, you can use `session.form()` to have the
    first form declared in the document (useful when you know that there is only
    a single form).
    
    Each form object can be easily manipulated using the
    following methods:

    >   form.fields()

    This will return a list of dictionaries representing the input elements
    constituting the form (that is `input`, `select`, `textarea`).
    
    Each dict contains the attributes of the HTML element. For select and
    textarea, the `type` and `value` attributes are set to the current value
    (selected option or text area content).

    >   >>> print form.fields()[0]
    >   {'name':'user', 'type':'text', value:''}

    This gives you the full details of the fields, but you can also get a
    shorter version with only the names:

    >   >>> print form.fieldNames()
    >   ('name',...)

    You may be tempted to change the value of a field directly, but you should
    *use the set() method instead* :

    >   form.set('user', ...)

    this is a better option, because changing the field value attribute will
    overwrite the default form value, while using the `set()` method will
    indicate that you specified a custom value for the field (which can be later
    cleared, so that the form object can be reused).
    
        Note____________________________________________________________________
        If you set values for _checkboxes_, they will be converted to `on` or
        `off`, unless their value is None, in which case they will be considered
        as undefined

    Aside from fields, you can have a list of the form `actions`, which are
    actually the inputs with `type=submit`.

    >   form.actions()

    this will return a list of actions (the `submit` elements`) that you can
    trigger when submitting the form. Here is an example:

    >   >>> Session("www.google.com").forms().actions()
    >   [{'type': 'submit', 'name': 'btnG', 'value': 'Google Search'}, 
    >    {'type': 'submit', 'name': 'btnI', 'value': "I'm Feeling Lucky"}]

    To submit your form, you can use the session `submit()` method, which takes
    the following arguments:

    - `action`, which is the form action (from `form.actions()`) you would like
      to use when submitting. If no action is specified, no default action will
      be choosen.

    - `values` is a dict of values that should be merged with the form already
      set and default values (note that it does not change the form values, such
      as what the form `set()` method does).

    - `attach` is a list of attachments (created with the session `attach()`
       method) that should be submitted with the form.

    - `method` is the HTTP method to use in the submission. If you specify
      attachments, then `POST` is required (and it is the default)

    - `strip` tells if fields with empty values should be present within
      generated request body. By default it is `True`, which is sensible in most
      cases. However, if your request fails, you should try to set `strip` to
      `False` and see if it succeeds like that.

    The session `submit(form)` method will actually invoke the form `submit()`
    method, and then pass the result to the session `post` or `get` method. So
    if you want to see how the forms creates a "submission request body", have a
    look at the `wwwclient.form.Form.submit()` method.

        Note ________________________________________________________________
        When _submitting forms_, you can specify whether you want _fields with
        no values_ to be _stripped_ or not. Depending on how the server is
        implemented, this may cause your request to be incorrectly processed or
        not.
        |
        If your request fails to be processed properly, try changing the value
        of the `strip` parameter in form submission methods.

Scraping
========

    We've seen how to browse, post data and how to submit forms. We've also
    briefly mentioned that the forms submission relies on the scraping module to
    extract information from the last transaction response data.

    In this section, we will see into detail how to use the scraping module to
    manipulate and extract parts of an HTML document.

Tag list and tag tree
---------------------

    We all know that browsers are very tolerant to crappy HTML, and that there
    are many ways to read and process an HTML document. Most existing tools will
    try to convert your document to a tree object with a DOM-like interface,
    which is actually very useful, but not all the time, and sometimes blatantly
    fails to create a useful representation of your HTML document.

    WWWClient scraping module is based on the principle that *you should be able
    to scrape HTML using string, list or tree operations*, because it is sometimes
    easier to identify a substring, extract it, and then work on it as subset of
    your HTML document.

    For instance, say you want to extract the ''most popular projects'' from the
    [Freshmeat](http://www.freshmeat.net) home page. By looking at the HTML, you
    will see that this information is contained in a table, like that :

    >     <b>MOST POPULAR PROJECTS</b>
    >   </div>
    >   <table border="0" cellpadding="2" cellspacing="0">
    >   ...
    >   </table>
    >   <br>
    >   <!-- DoubleClick Ad Tag -->

    In this respect, it would be very easy to get the table by looking for the
    `"MOST POPULAR PROJECTS"` string and then for the `"<!-- DoubleClick Ad"`
    right after, extract the substring between these two markers and process it.

    To do so, WWWClient offers you  operations to construct a _list of tags_
    from an HTML string (or substring), and then to ''fold'' this list of tags
    into a tree. The lists and tree can both be converted to the exact HTML
    string they represent, and you can switch anytime between the list and tree
    representations.

        Note __________________________________________________________________
        WWWClient tag list and tag tree were designed to be completely faithful
        to the original HTML. That means that if you convert a tag list or a tag
        tree to HTML, you will have *exactly* the same HTML string as the one
        you used to construct the structure.

    As an illustration, the Freshmeat most popular projects table looks like
    that:

    >     <tbody><tr valign="top">
    >       <td align="right">1.</td>
    >       <td><a href="/projects/mplayer/"><b><font color="#000000">MPlayer</font></b></a></td>
    >       <td align="right">100.00%</td>
    >     </tr>
    >           <tr valign="top">
    >       <td align="right">2.</td>
    >   
    >       <td><a href="/projects/linux/"><b><font color="#000000">Linux</font></b></a></td>
    >       <td align="right">81.03%</td>
    >     </tr>
    >     ... 
    >     </tbody>

    When you convert it to a list using the `wwwclient.scrape` `HTML.list(...)`
    function, you get this:

    >   ['<tbody>',
    >   '<tr valign="top">', '\n    ', '<td align="right">',
    >   '1.', '</td>', '\n    ', '<td>', '<a href="/projects/mplayer/">', '<b>',
    >   '<font color="#000000">', 'MPlayer', '</font>', '</b>', '</a>', '</td>',
    >   '\n    ', '<td align="right">', '100.00%', '</td>', '\n  ', '</tr>', '\n        ',
    >   '<tr valign="top">', '\n    ', '<td align="right">',
    >   '2.', '</td>', '\n\n    ', '<td>', '<a href="/projects/linux/">', '<b>',
    >   '<font color="#000000">', 'Linux', '</font>', '</b>', '</a>', '</td>', '\n    ',
    >   '<td align="right">', '81.03%', '</td>', '\n  ', '</tr>', '\n        ',
    >   ....

    when folded into a tree, or when you call `HTML.tree(...)`, you get something
    like that:

    >   #root
    >   +-- tbody#0@1:
    >       +-- tr#1@2:valign=top
    >           +-- #text:'\n    '
    >           +-- td#2@3:align=right
    >               +-- #text:'1.'
    >           +-- #text:'\n    '
    >           +-- td#3@3:
    >               +-- a#4@4:href=/projects/mplayer/
    >                   +-- b#5@5:
    >                       +-- font#6@6:color=#000000
    >                           +-- #text:'MPlayer'
    >           +-- #text:'\n    '
    >           +-- td#7@3:align=right
    >               +-- #text:'100.00%'
    >           +-- #text:'\n  '
    >       +-- #text:'\n        '
    >       +-- tr#8@2:valign=top
    >           +-- #text:'\n    '

    this tree representation shows you the `nodename#number@depth` where the
    number is the number of the node within the tree and the  `depth` is the
    number of ancestors of the node. All this information will be very useful
    when you will want to manipulate the data and extract the information you
    need.

    For the moment, all you need to know is that you can switch at any moment
    between the string, the _tag list_ and the _tag tree_ representation of your
    documents, or _fragments of it_. 


Getting to the desired data
---------------------------

    Let's start with a simple example: we want to search the web using Google
    and retrieve the searched items as a list.

    The first step is to get the desired data using the _browsing_ module:

    >   from wwwclient import browse, scrape
    >   s = browse.Session("http://www.google.com")
    >   f = s.form().fill(q="python web scraping")
    >   s.submit(f, action="btnG", method="GET")
    
    Now that we have submitted our query, we can simply have a look at the HTML.
    If you compare the HTML of a page retrieved using FireFox and a page
    retrieved using the basic WWWClient, you will notice a difference: Google
    actually do some user-agent detection (such as many sites, like Freshmeat).

    Looking at the HTML source code won't help that much, so that we can
    directly print a tree representation of the page:

    >   >>> tree = scrape.HTML.tree(s.page())
    >   >>> print tree
    
    I won't reproduce the whole tree here, but if you study the tree, you will
    notice that the elements we are interested in are:

    >    +-- #text:u' '
    >    +-- p#264@4:class=g
    >        +-- a#265@5:href=http://www.lib.uwaterloo.ca/~cpgray/project.html, class=l
    >            +-- #text:u'Metadata on the '
    >            +-- b#266@6:
    >                +-- #text:u'Web'
    >    +-- table#267@4:cellpadding=0, border=0, cellspacing=0
    >        +-- tr#268@5:
    >            +-- td#269@6:class=j
    >                +-- font#270@7:size=-1
    >                    +-- #text:u'By using Zope with the '
    >                    +-- b#271@8:
    >                        +-- #text:u'python'
    >                    +-- #text:u' urllib '
    >                     +-- b#272@8:
    >                         +-- #text:u'Web'

    these are actually the link title (#264) and the link extract (#267). We
    notice that link titles are `<p>`  of depth 4, and link descriptions are
    `<table>` of depth 4.

    Let's introduce the `cut()` method of the tag tree:
    
    cut::
        
        The `cut()` method allows to cut the tree so that it creates a subtree
        with all the nodes above, below, or in the cutting range.

        `tree.cut(below=4)` will return a subtree with all the nodes of the tree
        with a depth of 5 and more.

        `tree.cut(above=4)` will return a subtree with all the nodes of the tree
        with a depth of 3 or less.

    So the `cut()` method is actually what we are looking for, and calling

    >   subtree = tree.cut(below=3)

    will return us the data node with depth 4 and more in a new tag tree. We may
    now want to keep only the `<p>` and `<table>` elements.

    # FIXME: Not sure how this should work

    filter::

        The `filter()` method allows to create a new tag tree which content
        filtered by rejection (`reject`) or acceptation (`accept`) predicates.

    >   subtree = subtree.filter(accept=lambda n:n.name.lower() in ("table","p"))

    If we print the subtree, we will notice that it is still quite complex,
    having both font tags, and split strings. Now, for each child of our
    subtree, we could try to use text-conversion method (which will be presented
    later):

    >   for child in subtree.children:
    >       print "--------\n", HTML.text(child)

    The result is much more easy to read:

    >   ----------
    >   ASPN : Python Cookbook : Access password-protected web ...
    >   ----------
    >   ActiveState Open Source Programming tools for Perl Python XML xslt scripting
    >   with  free ... Title: Access password-protected web applications for
    >   scraping. ...aspn.activestate.com/ASPN/Cookbook/Python/Recipe/391929 - 26k -
    >   Cached - Similar&nbsp;pages
    >   ----------
    >   &quot;&quot;&quot;Python module for web browsing and scraping. Done: - navigate ...
    >   ----------
    >   &quot;&quot;&quot;Python module for web browsing and scraping. Done: -
    >   navigate to absolute and  relative URLs - follow links in page or region -
    >   find strings or regular ...zesty.ca/python/scrape.py - 31k - Cached -
    >   Similar&nbsp;pages

    with this representation, we can confirm that we have extracted the right
    information.

    If we want to select a particular subset of a node, like the `<a>` within
    the `<p>`, we can use the `elements()` method of the tag tree:

    find::

        The `find()` method allows to return a subset of the descendants of
        the given node that have the given name (`elements(withName=...)`) or
        depth (`elements(withDepth=...)`).

    We can modify slightly the above script to print the link along with the
    title:

    >   for node in nodes.children:
    >       print HTML.text(node)
    >       if node.name == "p":
    >           link = node.elements(withName="a")[0]
    >           print "-->", link.attribute("href")
    >       else:
    >           print "---------"

    We've seen the basic `cut`, `filter` and `find` functions of the tag tree.
    They consist in the most useful operations you can do with the tag tree, and
    the ones you are the most likely to use in your everyday scraping duties.
    

Web automation
--------------

    In addition to the basic tag tree operations, you can have access to higher
    level functions that will automatically extract _forms_ and _links_ for you.

    forms::

        The forms method scrapes the HTML document for forms and inputs
        (including `textarea`, `select`, and all the likes). The scraping
        algorithm will manage some borderline cases, such as definition of
        fields outside of a form.

        To use it, simply do:

        >   HTML.forms(tagtree or taglist or string)

    links::

        Pretty much like the `forms()` method, the `links()` method will return
        the list of links as `[(tagname, href),...]`. Links cover every HTML
        element that defines an `href` or `src` attribute, so that it includes
        images and iframes.

        In the above example:

        >   >>> HTML.links(link)
        >   [(u'a', u'http://www.gossamer-threads.com/lists/python/python/516801')]

    The web automation procedures all work with strings, tag list and tag trees,
    and are optimized for very fast information retrieval.

Text processing functions
-------------------------

    As we've seen, it is important to be able to easily convert between the
    string, the tag list and the tag tree. When manipulating the string
    representation, we may want to remove the HTML tags, normalize the spacing
    or expand the entities. 
    
    WWWClient offers functions to cover all these needs:

    expand::
        
        This function takes a string with HTML entities, and returns a version
        of the string with expanded entities.

        >   >>> scrape.HTML.expand("&quot;&quot;&quot;Python")
        >   '"""Python'

    norm::
        
        The `norm()` function replaces multiple spaces, tabs and newlines by
        a single space. This ensures that spacing in your text is consistent.

    text::

        The `text()` method automatically strips the tags from your document
        (it is a bit like stripping the tags from a tag list), and returns the
        text version of it. You can set the `expand` and `norm` parameters to
        pass the result to the `expand` and `norm` functions

    html::
    
        The `html()` method allows you to convert your taglist or tagtree to a
        string of HTML data. If you join a taglist created from an HTML string,
        it will be strictly identical to this string. 


    In addition to these basic functions, you also have the following
    convenient functions:

    textcut::
        
        Textcut allows to specify `cutfrom` and `cutto` markers (as strings)
        that will delimit the text range to be returned. For instance if you are
        looking for the text between `<p>` and `</p>`, you simply have to do:

        >   HTML.textcut(text, "<p>", "</p>")

        When the markers are not found, the start or end bounds of the text are
        used instead.

    textlines::

        Texlines allow to split your text in lines, optionally stripping
        (`strip`) the lines and filtering out empty lines (`empty`).

Tips
====

    1) Split your HTML into sections::

       Most HTML documents consist of different parts: headers, footers,
       navigation section, advertising, legal info, and actual content. It will
       be easier for you if you start by cutting and splitting your HTML
       document, getting rid of what you don't need and keeping what you are
       looking for.

    2) Get rid of HTML when you don't need structure::

       Manipulating HTML data can be difficult, especially when the document is
       not really well-formed. For instance, if you are scraping a document with
       table-formatted data, it may be complex to access the elements you need.

       In this case, it may be a better option to cut and split your HTML so
       that you have your ''sections of data'' at hand, and then convert them to
       text using `HTML.text(HTML.expand(html))`, and simply process the rest
       with the scraper module text processing tools or Python regular ones.


Text encoding support
=====================

    As text data may come from various sources, some may be already encoded or
    not.  To ensure that proper conversion is made, the following WWWClient
    elements feature an `encoding` property or argument to relevant methods that
    allows to specify in which encoding the given text data is encoded. This
    will ensure that the data is properly converted to raw strings before being
    passed to the transport layer (provided by the Curl library).

        Session::
          Session encoding defines the default encoding for all the requests,
          cookies, headers, parameters, fields and provided data. Setting a session
          encoding will set every transaction, request and underlying curl handler
          encodings to the session one.

        Form::
          when filling values within a form, the values will be converted to
          string when necessary. The given encoding will tell in which encoded the
          string should be coded.

Acknowledgments
===============

    I would like to thank Marc Carignan from [Xprima.com](http://www.xprima.com)
    for giving me the opportunity to work on the WWWClient project and let it be
    open-sourced. This project could not have happened without his help, thanks
    Marc !

    I would also like to thank the whole Python community for having created
    such an expressive, powerful language that have pleased me for years.

# vim: ts=4 sw=4 et syn=kiwi
