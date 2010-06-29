#!/bin/bash
for file in ../*.xml
do
	pref=`basename $file .xml`
        java -jar saxon9.jar $file workflow.xsl > $pref.html	
done
