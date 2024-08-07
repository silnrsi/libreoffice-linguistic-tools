"""
Write XSLT files to run against XML data files.
"""
import io
import datetime
import logging

logger = logging.getLogger("lingt.access.XSLTWriter")

class XSLT_Writer:
    def __init__(self, filepath):
        self.filepath = filepath

    def write(self, dataList, xpathsToSearch, matchPartial):
        """
        param dataList: List with rows containing two elements.
        param xpathsToSearch: List of XPath expressions.
        """
        logger.debug("writing XSLT file")
        with io.open(self.filepath, mode='w', encoding='UTF8') as outfile:
            now = datetime.datetime.now()
            header = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<!--\n'
                'This file was generated by LibreOffice Linguistic Tools.\n'
                'It makes changes to an XML file in order to correct spelling.\n'
                '\n'
                'Date Generated: %s.\n'
                '-->\n'
                '<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" '
                'version="1.0">\n'
                '<xsl:output method="xml" omit-xml-declaration="no"\n'
                '  encoding="utf-8"\n'
                '  indent="no"\n'
                '  doctype-system="" /><!-- Can specify DTD file here. -->\n'
                '\n'
                '<!-- This is called the identity template, because it\n'
                ' simply copies everything in the original file.  Everything,\n'
                ' that is, except for certain things we want to change, which\n'
                ' we specify in the template(s) that follow. -->\n'
                '<xsl:template match="@*|node()">'
                '<!-- This is shorthand for everything. -->\n'
                '  <xsl:copy>\n'
                '    <!-- Apply on all children recursively. -->\n'
                '    <xsl:apply-templates select="@*|node()"/>\n'
                '  </xsl:copy>\n'
                '</xsl:template>\n') % now.strftime("%d-%b-%Y")
            outfile.write(header)

            for xpath in xpathsToSearch:
                outfile.write(
                    '<!-- We want to change the value of this element. -->\n'
                    '<xsl:template match="%s">\n'
                    '  <xsl:call-template name="look4changes"/>\n'
                    '</xsl:template>\n' % xpath)

            outfile.write(
                '<xsl:template name="look4changes">\n'
                '  <xsl:copy>\n'
                '    <xsl:apply-templates select="@*" mode="copy_attrs"/>\n'
                '    <xsl:choose>\n')

            for replacement in dataList:
                oldVal, newVal = replacement
                if matchPartial:
                    outfile.write(
                        '      <xsl:when test="contains(text(), \'%s\')">\n'
                        '        <xsl:value-of select="concat(\n'
                        '           substring-before(text(), \'%s\'),\n'
                        '           \'%s\',\n'
                        '           substring-after(text(),  \'%s\'))" />\n'
                        '      </xsl:when>\n' % (oldVal, oldVal, newVal, oldVal))
                else:
                    outfile.write(
                        '      <xsl:when test="text() = \'%s\'">\n'
                        '        <xsl:text>%s</xsl:text>\n'
                        '      </xsl:when>\n' % (oldVal, newVal))

            outfile.write(
                '      <xsl:otherwise>\n'
                '        <!-- Copy text unchanged. -->\n'
                '        <xsl:value-of select="node()" />\n'
                '      </xsl:otherwise>\n'
                '    </xsl:choose>\n'
                '  </xsl:copy>\n'
                '</xsl:template>\n'
                '\n'
                '<!-- This simply copies all attributes of an element -->\n'
                '<xsl:template match="@*" mode="copy_attrs">\n'
                '  <xsl:copy/>\n'
                '</xsl:template>\n'
                '\n'
                '</xsl:stylesheet>\n')
        logger.debug("finished writing file")
