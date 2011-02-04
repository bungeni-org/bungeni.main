<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema" exclude-result-prefixes="xs" version="2.0">
    <xd:doc xmlns:xd="http://www.oxygenxml.com/ns/doc/xsl" scope="stylesheet">
        <xd:desc>
            <xd:p><xd:b>Created on:</xd:b> Jan 10, 2011</xd:p>
            <xd:p><xd:b>Author:</xd:b> undesa</xd:p>
            <xd:p></xd:p>
        </xd:desc>
    </xd:doc>
    
    <xsl:template match="workflow">
        <html>
         <head><title>WF Rework</title></head>
            <body>
        <table border="1">
            <thead>
                <th>
                    Transition Id
                </th>
                <th>
                    Source
                </th>
                <th>
                    Destination
                </th>
                <th>
                    Permission
                </th>
            </thead>
            <tbody>
            <xsl:apply-templates></xsl:apply-templates>
            </tbody>
        </table>
            </body>
        </html>
        
    </xsl:template>
    
    <xsl:template match="transition">
        <tr>
            <td><xsl:value-of select="@id" /></td>
            <td><xsl:value-of select="@source" /></td>
            <td><xsl:value-of select="@destination" /></td>
            <td><xsl:value-of select="@permission" /></td>
        </tr>
    </xsl:template>
    
    <xsl:template match="state"></xsl:template>
</xsl:stylesheet>
