import xml.etree.ElementTree as ET
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

class apply_inline():
    def error(self, msg):
        raise ValueError(f'at ch {self.current}: {msg}')

    def consume_inline_element(self, ch, tag):
        elem = ET.Element(tag)
        elem.text = ''
        self.next()
        while not self.at_end() and self.ch() != ch:
            elem.text += self.ch()
            self.next()

        if self.at_end():
            self.error(f'unmatched "{ch}".')
        self.next()
        self.push(elem)

    def consume_link(self):
        link = ET.Element('a', {'href': ''})
        link.text = ''
        self.next()
        while not self.at_end() and self.ch() != ']':
            link.text += self.ch()
            self.next()

        self.next()
        self.next()

        while not self.at_end() and self.ch() != ')':
            link.attrib['href'] += self.ch()
            self.next()

        self.next()
        self.push(link)

    def __call__(self, src):
        self.src = src
        self.current = 0
        self.paragraph = ET.Element('p')
        self.paragraph.text = ''
        self.latest = None

        while not self.at_end():
            match self.ch():
                case '*': self.consume_inline_element('*', 'i')
                case '`': self.consume_inline_element('`', 'code')
                case '[' if self.src.find('](', self.current):
                    self.consume_link()
                case c:
                    if self.latest is None:
                        self.paragraph.text += c
                    else:
                        self.latest.tail += c
                    self.next()

        return self.paragraph

    def at_end(self):
        return self.current >= len(self.src)

    def ch(self, pos=-1):
        if pos == -1:
            if self.at_end():
                return ''
            else:
                return self.src[self.current]
        else:
            return self.src[pos]

    def push(self, elem):
        self.paragraph.append(elem)
        self.latest = elem
        self.latest.tail = ''
        
    def next(self):
        self.current += 1
        return self.ch(self.current-1)

class to_html:
    def error(self, msg):
        raise ValueError(f'at line {self.current}: {msg}')

    def skip_whitespace(self):
        while not self.at_end() and self.is_line_empty():
            self.next()

    def consume_frontmatter(self):
        frontmatter = {}
        self.next()
        while not self.line().strip().startswith('---'):
            mid = self.line().find(':')
            if mid == -1:
                self.error('no ":" found in frontmatter pair.')
            frontmatter[self.line()[:mid]] = self.line()[mid+1:].strip()
            self.next()
        self.next()
        return frontmatter

    def consume_header(self, node):
        depth = 0
        for c in self.line():
            match c:
                case ' ': break
                case '#': depth += 1
                case c:
                    self.error(f'unrecognized character "{c}".')
        if depth > 5:
            self.error('inappropriate header depth.')
        ET.SubElement(node, f'h{depth}').text = self.line()[depth:].strip()
        self.next()

    def consume_bullet_list(self, node):
        bullet_list = ET.SubElement(node, 'ul')
        while self.line().startswith('-'):
            ET.SubElement(bullet_list, 'li').text = self.line()[1:].strip()
            self.next()

    def consume_ordered_list(self, node):
        ordered_list = ET.SubElement(node, 'ol')
        i = 1
        while self.line().startswith(f'{i}.'):
            ET.SubElement(ordered_list, 'li').text = self.line()[len(f'{i}.'):].strip()
            i += 1
            self.next()

    def consume_paragraph(self, node):
        paragraph = ET.SubElement(node, 'p')
        paragraph.text = self.line().strip()
        self.next()
        while not self.is_line_empty():
            paragraph.text += ' ' + self.line().strip()
            self.next()
        try:
            paragraph.append(apply_inline(paragraph.text))
            paragraph.text = ''
        except ValueError as e:
            self.error(e)

    def consume_code_block(self, node):
        lang = self.line()[3:].strip()
        code = ''
        self.next()
        while not self.line().startswith('```') and not self.at_end():
            code += self.line() + '\n'
            self.next()

        if self.at_end():
            self.error('unterminated code block.')

        if lang:
            node.append(ET.fromstring(highlight(
                code,
                get_lexer_by_name(lang),
                HtmlFormatter()
            )))
        else:
            ET.SubElement(ET.SubElement(node, 'pre'), 'code').text = code
        self.next()

    def __call__(self, src):
        self.src = src.splitlines()
        self.current = 0
        self.content = ET.Element('div', {'class': 'body'})

        frontmatter = {}
        first = True
        while not self.at_end():
            self.skip_whitespace()

            if first and self.line().strip() == '---':
                frontmatter = self.consume_frontmatter()
            elif self.line().strip().startswith('#'):
                self.consume_header(self.content)
            elif self.line().strip().startswith('-'):
                self.consume_bullet_list(self.content)
            elif self.line().strip().startswith('1.'):
                self.consume_ordered_list(self.content)
            elif self.line().startswith('```'):
                self.consume_code_block(self.content)
            else:
                self.consume_paragraph(self.content)
            self.start = self.current
            first = False

        return (ET.tostring(self.content, encoding='unicode', method='html'), frontmatter)

    def at_end(self):
        return self.current >= len(self.src)

    def line(self, pos=-1):
        if pos == -1:
            if self.at_end():
                return ''
            else:
                return self.src[self.current]
        else:
            return self.src[pos]

    def is_line_empty(self):
        return not self.line().strip()

    def next(self):
        if self.at_end():
            return ''
        self.current += 1
        return self.line(self.current-1)

to_html = to_html()
apply_inline = apply_inline()
