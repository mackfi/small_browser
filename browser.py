#!/usr/bin/env python3
import socket
import ssl
import os.path
from datetime import datetime
import tkinter
import tkinter.font


WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
SCROLL_STEP = 100
FONTS = {}
INHERITED_PROPERTIES = {
    "font-size": "16px",
    "font-style": "normal",
    "font-weight": "normal",
    "color": "black",
    "font-family" : "Times"
}

def set_parameters(**params):
	global WIDTH, HEIGHT, HSTEP, VSTEP, SCROLL_STEP
	if "WIDTH" in params: WIDTH = params["WIDTH"]
	if "HEIGHT" in params: HEIGHT = params["HEIGHT"]
	if "HSTEP" in params: HSTEP = params["HSTEP"]
	if "VSTEP" in params: VSTEP = params["VSTEP"]
	if "SCROLL_STEP" in params: SCROLL_STEP = params["SCROLL_STEP"]


class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window, 
            width=WIDTH,
            height=HEIGHT,
            bg="white"
        )
        self.canvas.pack(fill=tkinter.BOTH, expand=1)
        self.scroll = 0
        self.bookmarks = []
        # self.display_list = []
        # self.url = None
        self.tabs = []
        self.active_tab = None
        self.chrome = Chrome(self)
        self.window.bind("<Down>", self.handle_down)
        self.window.bind("<Up>", self.handle_up)
        self.window.bind("<Configure>", self.resize)
        self.window.bind("<MouseWheel>", self.handle_mousewheel)
        self.window.bind("<Button-1>", self.handle_click)
        self.window.bind("<Button-2>", self.handle_middle_click)
        self.window.bind("<Key>", self.handle_key)
        self.window.bind("<Return>", self.handle_enter)
        self.window.bind("<BackSpace>", self.handle_backspace)

    def new_tab(self, url):
        new_tab = Tab(HEIGHT - self.chrome.bottom, self)
        new_tab.load(url)
        self.active_tab = new_tab
        self.tabs.append(new_tab)
        self.draw()

    # def load(self, url):
        
        # self.draw()

    def draw(self):
        self.canvas.delete("all")
        self.active_tab.draw(self.canvas, self.chrome.bottom)
        for cmd in self.chrome.paint():
            cmd.execute(0, self.canvas)
            

    

    def resize(self, e):
        global WIDTH, HEIGHT
        WIDTH = e.width
        HEIGHT = e.height
        # self.document.layout()
        # self.display_list = self.document.display_list
        self.draw()

    

    def handle_down(self, e):
        self.active_tab.scrolldown()
        self.draw()

    def handle_up(self, e):
        self.active_tab.scrollup()
        self.draw()

    def handle_mousewheel(self, e):
        self.active_tab.mousewheel(e.delta)
        self.draw()

    def handle_click(self, e):
        if e.y < self.chrome.bottom:
            self.chrome.click(e.x, e.y)
        else:
            tab_y = e.y - self.chrome.bottom
            self.active_tab.click(e.x, tab_y)
        self.draw()

    def handle_middle_click(self, e):
        if e.y < self.chrome.bottom:
            pass
        else:
            tab_y = e.y - self.chrome.bottom
            self.active_tab.middle_click(e.x, tab_y, self)
        self.draw()

    def handle_key(self, e):
        if len(e.char) == 0: return
        if not (0x20 <= ord(e.char) < 0x7f): return
        self.chrome.keypress(e.char)
        self.draw()
        
    def handle_enter(self, e):
        self.chrome.enter()
        self.draw()

    def handle_backspace(self, e):
        self.chrome.backspace()
        self.draw()

class Rect:
    def __init__(self, left, top, right, bottom):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

    def __repr__(self):
        return "Rect({}, {}, {}, {})".format(self.left, self.top, self.right, self.bottom)

    def containsPoint(self, x, y):
        return x >= self.left and x < self.right \
            and y >= self.top and y < self.bottom

class DrawOutline:
    def __init__(self, rect, color, thickness):
        self.rect = rect
        self.color = color
        self.thickness = thickness

    def execute(self, scroll, canvas):
        canvas.create_rectangle(
            self.rect.left, self.rect.top - scroll,
            self.rect.right, self.rect.bottom - scroll,
            width=self.thickness,
            outline=self.color)

class DrawLine:
    def __init__(self, x1, y1, x2, y2, color, thickness):
        self.rect = Rect(x1, y1, x2, y2)
        self.color = color
        self.thickness = thickness

    def execute(self, scroll, canvas):
        canvas.create_line(
            self.rect.left, self.rect.top - scroll,
            self.rect.right, self.rect.bottom - scroll,
            fill=self.color, width=self.thickness)

class Chrome:
    def __init__(self, browser):
        self.browser = browser
        self.font = get_font(20, "normal", "roman", "serif")
        self.font_height = self.font.metrics("linespace")
        self.padding = 5
        self.tabbar_top = 0
        self.tabbar_bottom = self.font_height + 2*self.padding
        plus_width = self.font.measure("+") + 2*self.padding
        self.bottom = self.tabbar_bottom
        self.newtab_rect = Rect(
           self.padding, self.padding,
           self.padding + plus_width,
           self.padding + self.font_height)
        self.urlbar_top = self.tabbar_bottom
        self.urlbar_bottom = self.urlbar_top + \
            self.font_height + 2*self.padding
        self.bottom = self.urlbar_bottom
        back_width = self.font.measure("<") + 2*self.padding
        self.back_rect = Rect(
            self.padding,
            self.urlbar_top + self.padding,
            self.padding + back_width,
            self.urlbar_bottom - self.padding)
        
        self.address_rect = Rect(
            self.back_rect.top + self.padding,
            self.urlbar_top + self.padding,
            WIDTH - self.padding * 2 - 20,
            self.urlbar_bottom - self.padding,
        )

        self.bookmarks_rect = Rect(
            self.address_rect.right + self.padding,
            self.urlbar_top + self.padding,
            WIDTH - self.padding,
            self.urlbar_bottom - self.padding,
        )

        self.focus = None
        self.address_bar = ""
        
    def click(self, x, y):
        self.focus = None
        if self.newtab_rect.containsPoint(x, y):
            self.browser.new_tab(URL("https://browser.engineering/"))
        elif self.address_rect.containsPoint(x, y):
            self.focus = "address bar"
            self.address_bar = ""
        elif self.back_rect.containsPoint(x, y):
            self.browser.active_tab.go_back()
        elif self.bookmarks_rect.containsPoint(x, y):
            if str(self.browser.active_tab.url) in self.browser.bookmarks:
                self.browser.bookmarks.remove(str(self.browser.active_tab.url))
            else:
                self.browser.bookmarks.append(str(self.browser.active_tab.url))
        else:
            for i, tab in enumerate(self.browser.tabs):
                if self.tab_rect(i).containsPoint(x, y):
                    self.browser.active_tab = tab
                    break

    def keypress(self, char):
        if self.focus == "address bar":
            self.address_bar += char

    def enter(self):
        if self.focus == "address bar":
            self.browser.active_tab.load(URL(self.address_bar))
            self.focus = None

    def backspace(self):
        if self.focus == "address bar":
            self.address_bar = self.address_bar[:-1]

    def tab_rect(self, i):
        tabs_start = self.newtab_rect.right + self.padding
        tab_width = self.font.measure("Tab X") + 2*self.padding
        return Rect(
            tabs_start + tab_width * i, self.tabbar_top,
            tabs_start + tab_width * (i + 1), self.tabbar_bottom)

    def paint(self):
        cmds = []
        cmds.append(DrawRect(
            Rect(0, 0, WIDTH, self.bottom),
            "white"))
        cmds.append(DrawLine(
            0, self.bottom, WIDTH,
            self.bottom, "black", 1))
        cmds.append(DrawOutline(self.newtab_rect, "black", 1))
        cmds.append(DrawText(
            self.newtab_rect.left + self.padding,
            self.newtab_rect.top,
            "+", self.font, "black"))
        for i, tab in enumerate(self.browser.tabs):
            bounds = self.tab_rect(i)
            cmds.append(DrawLine(
                bounds.left, 0, bounds.left, bounds.bottom,
                "black", 1))
            cmds.append(DrawLine(
                bounds.right, 0, bounds.right, bounds.bottom,
                "black", 1))
            cmds.append(DrawText(
                bounds.left + self.padding, bounds.top + self.padding,
                "Tab {}".format(i), self.font, "black"))


            if tab == self.browser.active_tab:
                cmds.append(DrawLine(
                    0, bounds.bottom, bounds.left, bounds.bottom,
                    "black", 1))
                cmds.append(DrawLine(
                    bounds.right, bounds.bottom, WIDTH, bounds.bottom,
                    "black", 1))
                
            if self.focus == "address bar":
                cmds.append(DrawText(
                    self.address_rect.left + self.padding,
                    self.address_rect.top,
                    self.address_bar, self.font, "black"))
                w = self.font.measure(self.address_bar)
                cmds.append(DrawLine(
                    self.address_rect.left + self.padding + w,
                    self.address_rect.top,
                    self.address_rect.left + self.padding + w,
                    self.address_rect.bottom,
                    "red", 1))
            else:
                url = str(self.browser.active_tab.url)
                cmds.append(DrawText(
                    self.address_rect.left + self.padding,
                    self.address_rect.top,
                    url, self.font, "black"))
                
                    #E7.4
        if str(self.browser.active_tab.url) in self.browser.bookmarks:
            cmds.append(DrawRect(self.bookmarks_rect, "yellow"))
        cmds.append(DrawOutline(self.bookmarks_rect, "black", 1))

        cmds.append(DrawOutline(self.back_rect, "black", 1))
        cmds.append(DrawText(
            self.back_rect.left + self.padding,
            self.back_rect.top,
            "<", self.font, "black"))
        cmds.append(DrawOutline(self.address_rect, "black", 1))
        url = str(self.browser.active_tab.url) 
        cmds.append(DrawText(
                self.address_rect.left + self.padding,
                self.address_rect.top,
                self.address_bar, self.font, "black"))
        return cmds

class Tab:
    def __init__(self, tab_height, browser):
        # ...
        self.scroll = 0
        self.tab_height = tab_height
        self.history = []
        self.browser = browser

    
    def __repr__(self):
        return "Tab(history={})".format(self.history)

    def load(self, url):
        self.history.append(url)
        self.url = url
        body = url.request(self.browser)
        self.nodes = HTMLParser(body).parse()
        
        rules = DEFAULT_STYLE_SHEET.copy()
        style(self.nodes, sorted(rules, key=cascade_priority))

        links = [node.attributes["href"]
             for node in tree_to_list(self.nodes, [])
             if isinstance(node, Element)
             and node.tag == "link"
             and node.attributes.get("rel") == "stylesheet"
             and "href" in node.attributes]
        
        for link in links:
            try:
                body = url.resolve(link).request(self.browser)
            except:
                continue
            rules.extend(CSSParser(body).parse())

        self.document = DocumentLayout(self.nodes)
        self.document.layout()

        #E7.3
        if url.fragment != None:
            # print("FRAG:", url.fragment)
            self.scroll_to(url.fragment)


        self.display_list = []

        paint_tree(self.document, self.display_list)
    
    def scroll_to(self, fragment):
        for obj in tree_to_list(self.document, []):
            if isinstance(obj.node, Element):
                if (obj.node.attributes.get("id")==fragment):
                    self.scroll  =obj.y

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)

    def draw(self, canvas, offset):
        for cmd in self.display_list:
            if cmd.rect.top > self.scroll + self.tab_height:
                continue
            if cmd.rect.bottom < self.scroll: continue
            cmd.execute(self.scroll - offset, canvas)

    # The +/-40 in the following methods is something I added to be able to see the top/bottom of the page, kinda arbitrary
    def scrolldown(self):
        max_y = max(
            self.document.height + 2*VSTEP - self.tab_height, 0)
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)

    def scrollup(self):
        if (self.scroll - SCROLL_STEP < 0 - 40): return
        self.scroll -= SCROLL_STEP
        # self.draw()

    def mousewheel(self, delta):
        newScroll = self.scroll - delta
        max_y = max(self.document.height + 2*VSTEP - HEIGHT, 0)
        if (newScroll < 0 - 40): return
        if newScroll > 0:
            self.scroll = min(newScroll, max_y+40)
        else:
            self.scroll = newScroll
        # self.draw()

    

    def click(self, newX, newY):
        x, y = newX, newY
        y += self.scroll
        objs = [obj for obj in tree_to_list(self.document, [])
            if obj.x <= x < obj.x + obj.width
            and obj.y <= y < obj.y + obj.height]
        if not objs: return
        elt = objs[-1].node
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "a" and "href" in elt.attributes:
                if "#" == elt.attributes.get("href")[0]:
                    url = self.url
                    self.scroll_to(elt.attributes.get("href")[1:])
                    url.fragment = elt.attributes.get("href")[1:]
                else:
                    url = self.url.resolve(elt.attributes["href"])
                    return self.load(url)
            elt = elt.parent

    def middle_click(self, newX, newY, browser):
        x, y = newX, newY
        y += self.scroll
        objs = [obj for obj in tree_to_list(self.document, [])
            if obj.x <= x < obj.x + obj.width
            and obj.y <= y < obj.y + obj.height]
        if not objs: return
        elt = objs[-1].node
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "a" and "href" in elt.attributes:
                url = self.url.resolve(elt.attributes["href"])
                browser.new_tab(url)
                browser.active_tab = self
                return
            elt = elt.parent


class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent

    def __repr__(self):
        return repr(self.text)

class Element:
    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent
    def __repr__(self):
        attrs = [" " + k + "=\"" + v + "\"" for k, v  in self.attributes.items()]
        attr_str = ""
        for attr in attrs:
            attr_str += attr
        return "<" + self.tag + attr_str + ">"

def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)

def tree_to_list(tree, list):
    list.append(tree)
    for child in tree.children:
        tree_to_list(child, list)
    return list

class HTMLParser:
    SELF_CLOSING_TAGS = [
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
    ]
    HEAD_TAGS = [
        "base", "basefont", "bgsound", "noscript",
        "link", "meta", "title", "style", "script",
    ]
    
    def __init__(self, body):
        self.body = body
        self.unfinished = []
    def parse(self):
        text = ""
        in_comment = False
        in_tag = False
        in_script = False
        for i, c in enumerate(self.body):
            if in_script: 
                if c == "<":
                    if self.body[i+1: i+9] == "/script>":
                        in_tag = True
                        in_script = False
                        if text: self.add_text(text)
                        text = ""
                    else:
                        text += c
                else:
                    text += c
            else: 
                if c == "<":
                    if self.body[i+1 : i+4] == "!--":
                        in_comment= True
                    in_tag = True
                    if text: self.add_text(text)
                    text = ""
                elif c == ">":
                    if self.body[i-2 : i] == "--":
                        if self.body[i-4:i-2] != "<!" and self.body[i-5:i-2] != "<!-":
                            in_comment = False
                            in_tag = False
                    else:
                        if not in_comment:
                            in_tag = False
                            if text == "script":
                                in_script = True
                            elif text == "/script":
                                in_script = False
                            self.add_tag(text)
                            text = ""
                else:
                    if not in_comment:
                        text += c
        if not in_tag and text:
            
            self.add_text(text)
        return self.finish()
    
    def add_text(self, text):
        if text.isspace(): return
        self.implicit_tags(None)
        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)

    def add_tag(self, tag):
        tag, attributes = self.get_attributes(tag)
        if tag.startswith("!"): return
        self.implicit_tags(tag)
        buffer = []
        if tag.startswith("/"):
            if len(self.unfinished) == 1: return
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)

        elif tag in self.SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent)
            parent.children.append(node)

        else:
            if tag == "p":
                for i, unfinished_tag in enumerate(self.unfinished):
                    if unfinished_tag.tag == "p":
                        if i == len(self.unfinished) - 1:
                            u_parent = self.unfinished[i-1]
                            u_parent.children.append(unfinished_tag)
                            del self.unfinished[i]
                        else: 
                            for j in range(len(self.unfinished) - 1, i, -1):
                                u_parent = self.unfinished[j-1]
                                u_parent.children.append(self.unfinished[j])
                                unf = self.unfinished[j]
                                buffer.append(Element(unf.tag, unf.attributes, unf.parent))
                                del self.unfinished[j]
                            u_parent = self.unfinished[i-1]
                            u_parent.children.append(unfinished_tag)
                            del self.unfinished[i]
                parent = self.unfinished[-1] if self.unfinished else None
                node = Element(tag, attributes, parent)
                self.unfinished.append(node)
                while buffer:
                    self.unfinished.append(buffer.pop())
                return

            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag, attributes, parent)
            self.unfinished.append(node)

    def finish(self):
        if not self.unfinished:
            self.implicit_tags(None)
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()
    
    def get_attributes(self, text):
        parts = text.split()
        tag = parts[0].casefold()
        newText = ""
        for attr in parts[1:]:
            newText += attr + " "
        attributes = {}
        state = "in_spaces"
        buffer = ""
        key = ""
        doubleQuote = False
        singleQuote = False
        for c in newText[:-1]:
            if c == "\"":
                if state == "in_quotes":
                    if singleQuote and not doubleQuote:
                        buffer += "\""
                        doubleQuote = not doubleQuote
                    elif doubleQuote:
                        attributes[key.casefold()] = buffer
                        buffer = ""
                        key = ""
                        state = "in_spaces"
                elif state == "in_value":
                    state = "in_quotes"
                    doubleQuote = True


            elif c == "\'":
                if state == "in_quotes":
                    if doubleQuote and not singleQuote:
                        buffer += "\'"
                        doubleQuote = False
                    elif singleQuote:
                        attributes[key.casefold()] = buffer
                        buffer = ""
                        key = ""
                        state = "in_spaces"
                
                elif state == "in_value":
                    state = "in_quotes"
                    singleQuote = True

            elif c == "=":
                if state =="in_key":
                    state = "in_value"
                    key = buffer
                    buffer = ""
                elif state == "in_spaces":
                    state = "in_key"
                    buffer += c
                else:
                    buffer += c

            elif c == " ":
                if state == "in_key":
                    state = "in_spaces"
                elif state == "in_value":
                    attributes[key.casefold()] = buffer
                    buffer = ""
                    key = ""
                    state = "in_spaces"
                else:
                    buffer += c
            else:
                if state == "in_spaces":
                    state = "in_key"
                buffer += c
        if buffer != "":
            if key == "":
                attributes[buffer.casefold()] = key
            else:
                attributes[key.casefold()] = buffer

        return tag, attributes
    
    def implicit_tags(self, tag):
        while True:
            open_tags = [node.tag for node in self.unfinished]
            if open_tags == [] and tag != "html":
                self.add_tag("html")
            elif open_tags == ["html"] \
            and tag not in ["head", "body", "/html"]:
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")    
            elif open_tags == ["html", "head"] and \
            tag not in ["/head"] + self.HEAD_TAGS:
                self.add_tag("/head")
            else:
                break

class TagSelector:
    def __init__(self, tag):
        self.tag = tag
        self.priority = 1

    def __repr__(self):
        return "TagSelector(tag={}, priority={})".format(
            self.tag, self.priority)
    
    def matches(self, node):
        return isinstance(node, Element) and self.tag == node.tag

class CSSParser:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def whitespace(self):
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1

    def word(self):
        start = self.i
        while self.i < len(self.s):
            if self.s[self.i].isalnum() or self.s[self.i] in "#-.%":
                self.i += 1
            else:
                break
        if not (self.i > start):
            raise Exception("Parsing error")
        return self.s[start:self.i]
    
    def literal(self, literal):
        if not (self.i < len(self.s) and self.s[self.i] == literal):
            raise Exception("Parsing error")
        self.i += 1

    def pair(self):
        prop = self.word()
        self.whitespace()
        self.literal(":")
        self.whitespace()
        if prop.casefold() == 'font':
            i = self.i
            self.ignore_until([";", "}"])
            val = self.s[i:self.i].strip()
        else:
            val = self.word()
        return prop.casefold(), val
    
    def body(self):
        pairs = {}
        while self.i < len(self.s) and self.s[self.i] != "}":
            try:
                prop, val = self.pair()
                if prop == "font":
                    split_values = val.split(" ")
                    if (len(split_values) == 1):
                        pairs["font-family"] = split_values[0]
                    elif (len(split_values) == 2):
                        pairs["font-size"] = split_values[0]
                        pairs["font-family"] = split_values[1]
                    elif (len(split_values) == 3):
                        if (split_values[0] == "italic"):
                            pairs["font-style"] = split_values[0]
                        else:
                            pairs["font-weight"] = split_values[0]
                        pairs["font-size"] = split_values[1]
                        pairs["font-family"] = split_values[2]
                    elif (len(split_values) == 4):
                        pairs["font-style"] = split_values[0]
                        pairs["font-weight"] = split_values[1]
                        pairs["font-size"] = split_values[2]
                        pairs["font-family"] = split_values[3]
                    elif (len(split_values) > 4):
                        pairs["font-style"] = split_values[0]
                        pairs["font-weight"] = split_values[1]
                        pairs["font-size"] = split_values[2]
                        # check comment above if you want to skip needing join
                        font_family = """ """ .join(split_values[3:])
                        pairs["font-family"] = font_family
                
                else:
                    pairs[prop.casefold()] = val
                    self.whitespace()
                    self.literal(";")
                    self.whitespace()
            except Exception:
                why = self.ignore_until([";", "}"])
                if why == ";":
                    self.literal(";")
                    self.whitespace()
                else:
                    break
        return pairs
    
    def ignore_until(self, chars):
        while self.i < len(self.s):
            if self.s[self.i] in chars:
                return self.s[self.i]
            else:
                self.i += 1
        return None
    
    def selector(self):
        
        word = self.word()
        if word[0] == ".":
            out = ClassSelector(word[1:])
        else:
            out = TagSelector(word.casefold())
            # NEVER REACHES AFTER TAGSELECTOR
        
        self.whitespace()
        while self.i < len(self.s) and self.s[self.i] != "{":
            tag = self.word()
            if tag[0] == ".":
                descendant = ClassSelector(tag[1:])
            else:
                descendant = TagSelector(tag.casefold())
            out = DescendantSelector(out, descendant)
            self.whitespace()
        return out
    
    def parse(self):
        rules = []
        while self.i < len(self.s):
            try:
                self.whitespace()
                selector = self.selector()
                self.literal("{")
                self.whitespace()
                body = self.body()
                self.literal("}") 
                rules.append((selector, body))
            except Exception:
                why = self.ignore_until(["}"])
                if why == "}":
                    self.literal("}")
                    self.whitespace()
                else:
                    break
        return rules

def style(node, rules):
    node.style = {}
    for property, default_value in INHERITED_PROPERTIES.items():
        if node.parent:
            node.style[property] = node.parent.style[property]
        else:
            node.style[property] = default_value
    
    for selector, body in rules:
        if not selector.matches(node): continue
        for property, value in body.items():
            node.style[property] = value
    
    if isinstance(node, Element) and "style" in node.attributes:
        pairs = CSSParser(node.attributes["style"]).body()
        for property, value in pairs.items():
             node.style[property] = value
            
    if node.style["font-size"].endswith("%"):
        if node.parent:
            parent_font_size = node.parent.style["font-size"]
        else:
            parent_font_size = INHERITED_PROPERTIES["font-size"]
        node_pct = float(node.style["font-size"][:-1]) / 100
        parent_px = float(parent_font_size[:-2])
        node.style["font-size"] = str(node_pct * parent_px) + "px"

    for child in node.children:
        style(child, rules)

DEFAULT_STYLE_SHEET = CSSParser(open("browser.css").read()).parse()


    
class DescendantSelector:
    def __init__(self, ancestor, descendant):
        self.ancestor = ancestor
        self.descendant = descendant
        self.priority = ancestor.priority + descendant.priority

    def __repr__(self):
        return ("DescendantSelector(ancestor={}, descendant={}, priority={})") \
            .format(self.ancestor, self.descendant, self.priority)

    def matches(self, node):
        if not self.descendant.matches(node): return False
        while node.parent:
            if self.ancestor.matches(node.parent): return True
            node = node.parent
        return False

def cascade_priority(rule):
    selector, body = rule
    return selector.priority

class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.children = []
        self.x = None
        self.y = None
        self.width = None
        self.height = None

    def __repr__(self):
        return "DocumentLayout()"

    def layout(self):
        child = BlockLayout(self.node, self, None)
        self.children.append(child)
        self.display_list = child.display_list
        self.width = WIDTH - 2*HSTEP
        self.x = HSTEP
        self.y = VSTEP
        child.layout()
        self.height = child.height

    def paint(self):
        return []

BLOCK_ELEMENTS = [
    "html", "body", "article", "section", "nav", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
    "footer", "address", "p", "hr", "pre", "blockquote",
    "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
    "figcaption", "main", "div", "table", "form", "fieldset",
    "legend", "details", "summary"
]
class BlockLayout:
    def __init__(self, nodes):
        self.nodes = nodes
        self.node = nodes[0]
        self.display_list = []
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.cursor_x = 0
        self.cursor_y = 0
        self.centered = False
        self.superscript = False
        self.abbr = False
        self.line = []
        
    def __init__(self, nodes, parent, previous):
        if not isinstance(nodes, list):
            self.nodes = [nodes]
        else:
            self.nodes = nodes
        self.node = self.nodes[0]
        self.parent = parent
        self.previous = previous
        self.children = []
        self.display_list = []
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.height_of_line = 0
        self.cursor_x = 0
        self.cursor_y = 0
        self.centered = False
        self.superscript = False
        self.abbr = False
        self.line = []
    
    def __repr__(self):
        return "BlockLayout(x={}, y={}, width={}, height={})".format(
            self.x, self.y, self.width, self.height)

    def paint(self):
        cmds = []

        bgcolor = self.nodes[0].style.get("background-color",
                                      "transparent")
        if bgcolor != "transparent":
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.self_rect(), bgcolor)
            cmds.append(rect)
        
        if len(self.nodes) == 1 and isinstance(self.nodes[0], Element) and self.nodes[0].tag == "li":
            rect = DrawRect(Rect(self.x - (HSTEP + 2), self.y + (self.height_of_line / 2 - 2), 
                    self.x - (HSTEP - 2), self.y + 4 + (self.height_of_line / 2 - 2)), "black")
            cmds.append(rect)
        if len(self.nodes) == 1 and isinstance(self.nodes[0], Element) and self.nodes[0].tag == "nav" and \
            "class" in self.nodes[0].attributes and "links" in self.nodes[0].attributes["class"]:
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.self_rect(), "lightgray")
            cmds.append(rect)
        if len(self.nodes) == 1 and isinstance(self.nodes[0], Element) and self.nodes[0].tag == "pre":
                x2, y2 = self.x + self.width, self.y + self.height
                rect = DrawRect(self.self_rect(), "gray")
                cmds.append(rect)
        if self.layout_mode() == "inline":
            for x, y, word, color, font in self.display_list:
                cmds.append(DrawText(x, y, word, font, color))

        
        return cmds

    def layout(self):
        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y
        if isinstance(self.nodes[0], Element) and self.nodes[0].tag == "li":
            self.x = self.parent.x + (2 * HSTEP)
            self.width = self.parent.width - (2 * HSTEP)
        else:
            width = self.nodes[0].style.get("width", "auto")
            self.x = self.parent.x 
            if width == "auto":
                self.width = self.parent.width
            else:
                widthAsFloat = float(width[:-2])
                if widthAsFloat < 0:
                    self.width = self.parent.width
                else:
                    self.width = widthAsFloat
            # self.x = self.parent.x
            # self.width = self.parent.width
        mode = self.layout_mode()
        if mode == "block":
            previous = None
            buffer = []
            for child in self.nodes[0].children:
                if isinstance(child, Element) and child.tag =="head": 
                    continue
                if isinstance(child, Element) and child.tag in BLOCK_ELEMENTS:
                    if buffer:
                        newBlock = BlockLayout(buffer, self, previous)
                        # append the BlockLayout to children.
                        self.children.append(newBlock)
                        # clear the buffer
                        previous = newBlock
                        buffer = []
                else:
                    buffer.append(child)
                    continue
                    
                next = BlockLayout(child, self, previous)
                self.children.append(next)
                previous = next

            if buffer:
                newBlock = BlockLayout(buffer, self, previous)
                self.children.append(newBlock)

        else:
            # Assignment 7 code
            
            # self.recurse(self.node)

            # self.cursor_x = 0
            # self.cursor_y = 0
            # self.weight = "normal"
            # self.style = "roman"
            # self.size = 16

            # self.line = []
            self.new_line()
            for node in self.nodes:
                self.recurse(node)
            
            # self.flush()
        for child in self.children:
            child.layout()
        
        # New
        self.height = sum([child.height for child in self.children])

        # for child in self.children:
        #     self.display_list.extend(child.display_list)

    def layout_mode(self):
        if len(self.nodes) > 1:
            return "inline"
        elif isinstance(self.nodes[0], Text):
            return "inline"
        elif any([isinstance(child, Element) and \
                  child.tag in BLOCK_ELEMENTS
                  for child in self.nodes[0].children]):
            return "block"
        elif self.nodes[0].children:
            return "inline"
        else:
            return "block"
        

    def open_tag(self, tag):
        if tag == "i":
            self.style = "italic"
        elif tag == "b":
            self.weight = "bold"
        elif tag == "small":
            self.size -= 2
        elif tag == "big":
            self.size += 4
        elif tag == "br":
            self.new_line()
            # self.cursor_y += VSTEP
        elif tag == "h1 class=\"title\"":
            self.new_line()
            self.centered = True
        elif tag == "sup":
            self.superscript = True
            self.size //= 2
        elif tag=="abbr":
            self.abbr = True

    def close_tag(self, tag):
        if tag == "i":
            self.style = "roman"
        elif tag == "b":
            self.weight = "normal"
        elif tag == "small":
            self.size += 2
        elif tag == "big":
            self.size -= 4
        elif tag == "p":
            self.new_line()
        elif tag == "h1":
            self.new_line()
            self.centered = False
        elif tag == "sup":
            self.superscript = False
            self.size *= 2
        elif tag=="abbr":
            self.abbr = False
        
    def recurse(self, node):
        if isinstance(node, Text):
            for word in node.text.split():
                self.word(node, word)
        else:
            if node.tag == "br":
                self.new_line()
            for child in node.children:
                self.recurse(child)


    def word(self, node, word):
        family = node.style["font-family"]
        color = node.style["color"]
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        if style == "normal": style = "roman"
        size = int(float(node.style["font-size"][:-2]) * .75)
        font = get_font(size, weight, style, family)
        color = node.style["color"]
        # if self.abbr:
        #     font = get_font(size//2, "bold", style, family)
        # else:
        #     font = get_font(size, sweight, style, family)

        buffer = ""
        isLower = word[0].islower()
        if self.abbr:
            for c in word:
                if c.islower() == isLower:
                    buffer += c
                    continue
                if c.islower():      
                    font = get_font(size, weight, style, family)
                    isLower = True
                    self.line.append((self.cursor_x, buffer, font, color, self.superscript))
                    self.cursor_x += font.measure(buffer)
                    buffer = ""
                else:   
                    font = get_font(size//2, "bold", style, family)
                    buffer = buffer.upper()
                    isLower = False
                    self.line.append((self.cursor_x, buffer, font, color, self.superscript))
                    self.cursor_x += font.measure(buffer)
                    buffer = ""
                buffer += c

            if word[-1].islower():
                buffer = buffer.upper()
                font = get_font(self.size//2, "bold", style, family)
            else:
                font = get_font(self.size, self.weight, style, family)
            self.line.append((self.cursor_x, buffer, font, color, self.superscript))
            self.cursor_x += font.measure(buffer)
            font = get_font(self.size, self.weight, style, family)
            self.cursor_x += font.measure(" ")
            return

        w = font.measure(word)
        # print ("CURSOR_X + W:", self.cursor_x + w )
        # print ("width:", self.width)
        if self.cursor_x + w > self.width:
            if "\N{soft hyphen}" in word:
                buffer = ""
                wordArray = word.split("\N{soft hyphen}")
                for section in wordArray:
                    if self.cursor_x + font.measure(buffer + section + "-") <= WIDTH - HSTEP:
                        buffer += section
                    else:
                        self.word(node, buffer + "-")
                        buffer = section
                        self.new_line()
                self.word(node, buffer)
                return
            
            self.new_line()

            # self.cursor_x = HSTEP

        # self.line.append((self.cursor_x, word, font, color, self.superscript))
        self.cursor_x += w + font.measure(" ")

        # Chapter 7 Addition

        line = self.children[-1]
        previous_word = line.children[-1] if line.children else None
        text = TextLayout(node, word, line, previous_word)
        line.children.append(text)
        # self.cursor_x += text.width

    def flush(self):
        if not self.line: return
        offset = 0
        if self.centered:
            linewidth = self.line[-1][0] + self.line[-1][2].measure(self.line[-1][1]) - self.line[0][0]
            linestart = WIDTH/2 - linewidth/2
            offset = linestart - self.line[0][0]

        max_ascent = max([font.metrics("ascent")
            for x, word, font, color, sup in self.line])
        baseline = self.cursor_y + 1.25 * max_ascent
        for rel_x, word, font, color, sup in self.line:
            x = self.x + rel_x
            y = self.y + baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, color, font))
        max_descent = max([font.metrics("descent")
        for x, word, font, color, sup in self.line])

        metrics = [font.metrics() for x, word, font, color, sup in self.line]
        
        self.height_of_line = (1.25 * max_descent) + (1.25 * max_ascent)
        self.cursor_y = baseline + 1.25 * max_descent
        self.cursor_x = 0
        self.line = []

    def new_line(self):
        self.cursor_x = 0
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.nodes[0], self, last_line)
        self.children.append(new_line)

    def self_rect(self):
        return Rect(self.x, self.y,
            self.x + self.width, self.y + self.height)

class LineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []

    def __repr__(self):
        return "LineLayout(x={}, y={}, width={}, height={})".format(
            self.x, self.y, self.width, self.height)
    
    def layout(self):
        self.width = self.parent.width
        self.x = self.parent.x

        # print("X:", self.x)
        # print("width:", self.width)

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        for word in self.children:
            word.layout()

        # print("WTF:", [word.font.metrics("ascent") for word in self.children])
        if not self.children:
            self.height = 0
            return

        max_ascent = max([word.font.metrics("ascent") for word in self.children])
        baseline = self.y + 1.25 * max_ascent
        for word in self.children:
            word.y = baseline - word.font.metrics("ascent")
        max_descent = max([word.font.metrics("descent")
                        for word in self.children])
        self.height = 1.25 * (max_ascent + max_descent)

    def paint(self):
        return []

class TextLayout:
    def __init__(self, node, word, parent, previous):
        self.node = node
        self.word = word
        self.children = []
        self.parent = parent
        self.previous = previous
        self.width = 0
        self.height = 0

    def __repr__(self):
        return ("TextLayout(x={}, y={}, width={}, height={}, word={})").format(
            self.x, self.y, self.width, self.height, self.word)

    def layout(self):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        family = self.node.style["font-family"]
        if style == "normal": style = "roman"
        size = int(float(self.node.style["font-size"][:-2]) * .75)
        self.font = get_font(size, weight, style, family)

        self.width = self.font.measure(self.word)

        if self.previous:
            space = self.previous.font.measure(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        self.height = self.font.metrics("linespace")

        # print("X:", self.x)
        # print("height:", self.height)

    def paint(self):
        color = self.node.style["color"]
        return [DrawText(self.x, self.y, self.word, self.font, color)]

class ClassSelector:
    def __init__(self, classname):
        self.classname=classname 
        self.priority=10
    def __repr__(self):
        return "ClassSelector(classname={}, priority={})".format(
        self.classname, self.priority) 
    def matches(self, node):
        nodeClasses = node.attributes.get("class","")
        Split_node_classes = nodeClasses.split()
        return isinstance(node, Element) and self.classname in Split_node_classes

class DrawText:
    def __init__(self, x1, y1, text, font, color):
        self.top = y1
        self.left = x1
        self.text = text
        self.font = font
        self.bottom = y1 + font.metrics("linespace")
        self.color = color
        self.rect = Rect(self.left, self.top, self.left, self.top)

    def __repr__(self):
        return "DrawText(top={} left={} bottom={} text={} font={})" \
            .format(self.top, self.left, self.bottom, self.text, self.font)
    def execute(self, scroll, canvas):
        canvas.create_text(
            self.left, self.top - scroll,
            text=self.text,
            font=self.font,
            anchor='nw',
            fill=self.color)
    
class DrawRect:
    def __init__(self, x1, y1, x2, y2, color):
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color
        self.rect = Rect(self.left, self.top, self.right, self.bottom)

    def __init__(self, rect, color):
        self.top = rect.top
        self.left = rect.left
        self.bottom = rect.bottom
        self.right = rect.right
        self.color = color
        self.rect = rect
    
    def __repr__(self):
        return "DrawRect(top={} left={} bottom={} right={} color={})".format(
            self.top, self.left, self.bottom, self.right, self.color)
    def execute(self, scroll, canvas):
        canvas.create_rectangle(
            self.left, self.top - scroll,
            self.right, self.bottom - scroll,
            width=0,
            fill=self.color)

def paint_tree(layout_object, display_list):
        display_list.extend(layout_object.paint())
        for child in layout_object.children:
            paint_tree(child, display_list)

def get_font(size, weight, slant, family):
    key = (size, weight, slant, family)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight,
            slant=slant, family=family)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]

class URL:
    # Global caches, stores requests for a specified amount of time.
    cache = {}
    cacheTimes = {}
    def __init__(self, url):
        self.scheme, url = url.split("://", 1)
        if "/" in self.scheme:
            self.scheme = self.scheme[1:]
        assert self.scheme in ["http", "https", "file", "about"]
        
        if self.scheme == "file":
            self.path = url
        if "/" not in url:
            url = url + "/"
            # return
        self.host, url = url.split("/", 1)
        self.path = "/" + url
        
        self.fragment = None
        if "#" in self.path:
            self.path, self.fragment = self.path.split("#")

        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443
        elif self.scheme == "about":
            self.port = None
            self.host = None
            self.path = "bookmarks"
            return


        # Port check
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)

    def __repr__(self):
        fragment_part = "" if self.fragment == None else ", fragment=" + self.fragment
        return "URL(scheme={}, host={}, port={}, path={!r}{})".format(
            self.scheme, self.host, self.port, self.path, fragment_part)

    def request(self, browser, headers = None):
        s = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )

        request_dictionary = {}

        if headers != None:
            for key, value in headers.items():
                request_dictionary[key.lower()] = value

        if self.scheme == "about":
            http_body = "<!doctype html>"
            for bookmark in browser.bookmarks:
                http_body += f'<a href="{bookmark}">{bookmark}</a><br>'
            return http_body

        if self.scheme == "file":
            return self.openFile(f"{self.path}")

        # Creates secure port connection if https scheme used.
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)
        s.connect((self.host, self.port))

        # Retreives information from cache if available.
        if self.cache:
            key = f"{self.scheme}://{self.host}:{self.port}{self.path}"
            if key in self.cache.keys() :
                secDifference = datetime.now() - self.cacheTimes[key][0]
                if secDifference.total_seconds() < self.cacheTimes[key][1]:
                    return self.cache[key]

        requestString = "GET {} HTTP/1.1\r\n".format(self.path) + \
                        "host: {}\r\n".format(self.host)

        for key, value in request_dictionary.items():
            
            if key not in requestString:
                requestString += f"{key}: {value}\r\n"

        if "connection" not in requestString:
            requestString += "connection: close\r\n"
        if "user-agent" not in requestString:
            requestString += "user-agent: Mack\r\n"
        requestString += "\r\n"

        s.send((requestString)
               .encode("utf8"))
        
        response = s.makefile("r", encoding="utf8", newline="\r\n")
        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)

        

        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n": break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()

        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers

        body = response.read()
        s.close()

        # Adds to cache if applicable.
        if status.startswith("2"):
            
            if "cache-control" in response_headers:
                if "max-age" in response_headers["cache-control"]:
                    key = f"{self.scheme}://{self.host}:{self.port}{self.path}"
                    timeAgePair = (datetime.now(), float(response_headers["cache-control"].split("=")[1]))
                    self.cache[key] = body
                    self.cacheTimes[key] = timeAgePair

        # Redirects if applicable.
        if status.startswith("3") and "location" in response_headers.keys():
            location = response_headers["location"]
            if location.startswith("/"):
                return URL(f"{self.scheme}://{self.host}{location}").request()
            else:
                return URL(location).request()

        return body
    
    def openFile(self, url = ""):
        if not os.path.isfile(url):
            raise Exception
        if url != "":
            return open(url).read()
        
    def resolve(self, url):
        if not url.startswith("/"):
            dir, _ = self.path.rsplit("/", 1)
            while url.startswith("../"):
                _, url = url.split("/", 1)
                if "/" in dir:
                    dir, _ = dir.rsplit("/", 1)
            url = dir + "/" + url
        if "://" in url: return URL(url)
        if not url.startswith("/"):
            dir, _ = self.path.rsplit("/", 1)
            url = dir + "/" + url
        if url.startswith("//"):
            return URL(self.scheme + ":" + url)
        else:
            return URL(self.scheme + "://" + self.host + \
                       ":" + str(self.port) + url)
        
    def __str__(self):
        port_part = ":" + str(self.port)
        if self.scheme == "https" and self.port == 443:
            port_part = ""
        if self.scheme == "http" and self.port == 80:
            port_part = ""

        if self.scheme == "about":
            return "about://" + self.path

        if (self.fragment != None):
            return self.scheme + "://" + self.host + port_part + self.path + "#" +self.fragment
        else: 
            return self.scheme + "://" + self.host + port_part + self.path
    
def show(body):
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            print(c, end="")

def load(url):
    body = url.request()
    show(body)

# Entry point
if __name__ == "__main__":
    import sys
    Browser().new_tab(URL(sys.argv[1]))
    tkinter.mainloop()
    body = URL(sys.argv[1]).request()
    nodes = HTMLParser(body).parse()
    print_tree(nodes)

GRINNING_FACE_IMAGE = tkinter.PhotoImage(file="openmoji/1F600.png")
