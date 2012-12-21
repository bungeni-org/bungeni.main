Every logged in user gets a workspace with 4 tabs
  # drafts - items that the user is currently working on
  # inbox - items that require the users immediate attention
  # pending - items that the user previously worked on and that no longer require the users attention
  # archive - the documents whose workflows the user was directly involved in but which have now reached the end of their life-cycle

Configuration, like for the workflows, is per document. For each state of the document, one specifies which tabs and for which roles the document should appear in the workspace. For example, the configuration for bills is in bill.xml
<workspace id="bill">
    <state id="draft">
        <tab id="draft" roles="bungeni.Owner"/>
    </state>
...
</workspace>
In this case a bill in draft state will only appear in the Owner's workspace and it will be in his draft tab.
