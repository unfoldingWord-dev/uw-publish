# Steps for Publishing translationAcademy

1. Update some records in the tD database.
    ```
    delete from publishing_resourcedocument where publish_request_id = 81;
    update publishing_publishrequest set approved_at = null where id = 81;
    ```
1. Run tD.
1. Approve publish request #81. This will gather the Door43 pages and create a JSON record.
1. Select the JSON data you just created.
    ````
    select json_data from publishing_resourcedocument where publish_request_id = 81;
    ````
1. Past this data into `ta-en.json` and reformat to make it more readable.
1. Update the version number and any other fields in the JSON `meta` section.
1. FTP to `us.door43.org`.
1. On `us.door43.org`:
    ```
    sudo SSH_AUTH_SOCK=$SSH_AUTH_SOCK bash
    cd /var/www/vhosts/api.unfoldingword.org/ta/txt/1/en
    rm ta-en.json
    mv /home/phopper/ta-en.json ta-en.json
    chown syncthing:syncthing ta-en.json
    exit
    ```
1. In the `unfoldingWord.github.io` repository, update `_includes/ta_body.html` with the correct version number and PDF file name.
1. Commit the changes to the `master` branch and push to origin. This will update the `test.unfoldingword.org` site.
1. Have more than one person verify that `test.unfoldingword.org/academy/` is correct.
1. In the `unfoldingWord.github.io` repository, run `make publish` to push the changes to the production site.
