<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema" exclude-result-prefixes="xs" version="2.0">
    <xd:doc xmlns:xd="http://www.oxygenxml.com/ns/doc/xsl" scope="stylesheet">
        <xd:desc>
            <xd:p><xd:b>Created on:</xd:b> Jun 14, 2010</xd:p>
            <xd:p><xd:b>Author:</xd:b> undesa</xd:p>
            <xd:p></xd:p>
        </xd:desc>
    </xd:doc>
	<!-- This XSLT file generates tabular documentation out of the workflow xml files 
	To use it you need to use a XSLT 2 compliant processor e.g. Saxon. Transform is run directly
	on the workflow xml files -- and the output is a HTML document with 2 tables depicting the
	workflow states and transitions -->    
    <xsl:template match="workflow">
        <html>
            <head>
                <title><xsl:value-of select="@title"></xsl:value-of></title>
            <style>
            table {
	font: 11px/24px Verdana, Arial, Helvetica, sans-serif;
	border-collapse: collapse;
	width: 320px;
	}

th {
	padding: 0 0.5em;
	text-align: left;
	}

tr.yellow td {
	border-top: 1px solid #FB7A31;
	border-bottom: 1px solid #FB7A31;
	background: #FFC;
	}

td {
	border-bottom: 1px solid #CCC;
	padding: 0 0.5em;
	vertical-align:top;
	}

td:first-child {
	width: 190px;
	}

td+td {
	border-left: 1px solid #CCC;
	text-align: center;
	}
	
tr.m0 {background-color: #ffffcc;}
tr.m1 {background-color: #ffffff;}
tr.s0 { background-color: #eee; }
tr.s1 { background-color: #fff; }
	
 
            </style>
            </head>
            <h1><xsl:value-of select="@title"></xsl:value-of> States</h1>           
            <table  border="1">
                <tr class="yellow"><td>State Name</td><td>Allow</td><td>Deny</td></tr>
            <xsl:for-each select="./state">
                <xsl:call-template name="match-state"></xsl:call-template>
            </xsl:for-each>
            </table>
            <h1><xsl:value-of select="@title"></xsl:value-of> Transitions</h1>           
            
            <table  border="1">
                <tr class="yellow"><td>Transition Name</td><td>Source</td><td>Destination</td></tr>
                <xsl:for-each select="./transition">
                    <xsl:call-template name="match-transition"></xsl:call-template>
                </xsl:for-each>
            </table>
            
             </html>
    </xsl:template>
    
    <xsl:template name="match-state">
        <xsl:variable name="counter"><xsl:number /></xsl:variable>
        <tr class="m{$counter mod 2}">
            <td><a name="{@id}"></a>
                <xsl:value-of select="@title"></xsl:value-of></td>
            <td>&#160;
                <table border="0">
                <xsl:call-template name="grants"></xsl:call-template>
                </table>
            </td>
            <td>&#160;
                <table border="0">
                    <xsl:call-template name="denies"></xsl:call-template>
                </table>
            </td>
        </tr>
    </xsl:template>
  
    <xsl:template name="match-transition">
        <xsl:variable name="counter"><xsl:number /></xsl:variable>
        <tr class="m{$counter mod 2}">
            <td><xsl:value-of select="@title"></xsl:value-of></td>
            <td><xsl:variable name="tokSource" select="tokenize(@source, '\s+')">
            </xsl:variable>
                <xsl:for-each select="$tokSource">
                    <a>
                        <xsl:attribute name="href"><xsl:text>#</xsl:text><xsl:value-of select="."></xsl:value-of>
                        </xsl:attribute>
                        <xsl:value-of select="."></xsl:value-of>
                    </a><br />
                </xsl:for-each>
            </td>
            <td><xsl:variable name="tokDest" select="tokenize(@destination, '\s+')">
            </xsl:variable>
                <xsl:for-each select="$tokDest">
                    <a>
                        <xsl:attribute name="href"><xsl:text>#</xsl:text><xsl:value-of select="."></xsl:value-of>
                        </xsl:attribute>
                        <xsl:value-of select="."></xsl:value-of>
                    </a><br />
                </xsl:for-each>
            </td>
        </tr>
    </xsl:template>
    
    <xsl:template name="grants">
        <tr><td>Permission</td><td>Role</td></tr>
        <xsl:for-each select="./grant">
            <xsl:variable name="counter">
                <xsl:value-of select="position()"></xsl:value-of>
            </xsl:variable>
            <tr class="s{$counter mod 2}">
            <td><xsl:value-of select="substring-after(@permission, '.')"></xsl:value-of></td><td> <xsl:value-of select="@role"></xsl:value-of></td>
            </tr>
        </xsl:for-each>
    </xsl:template>
    
    <xsl:template name="denies">
        <tr><td>Permission</td><td>Role</td></tr>
        <xsl:for-each select="./deny">
            <xsl:variable name="counter">
                <xsl:value-of select="position()"></xsl:value-of>
            </xsl:variable>
            <tr class="s{$counter mod 2}">
                <td><xsl:value-of select="substring-after(@permission, '.')"></xsl:value-of></td><td> <xsl:value-of select="@role"></xsl:value-of></td>
            </tr>
        </xsl:for-each>
        
    </xsl:template>
    
</xsl:stylesheet>
