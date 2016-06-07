# Steps for unpublishing a Bible

### Removing a Bible from api.unfoldingword.org

* Run these commands on the us.door43.org server:
    ```
    sudo SSH_AUTH_SOCK=$SSH_AUTH_SOCK bash
    
    cd /var/www/vhosts/api.unfoldingword.org/httpdocs/ulb/txt/1
    rm -rf ulb-sr
    cd /var/www/vhosts/api.unfoldingword.org/httpdocs/ts/txt/2
    
    // test to see if the correct list of directories is returned
    find . -type d -name sr
    
    // or maybe like this 
    find . -type d ! -path './2/*/*/avd' -path './2/*/avd'
    
    // remove matching files
    find . -type d -name sr -exec rm -rf {} \;
    
    cd /home/phopper/uw-publish
    python execute.py update_catalog
    ```


### Removing a Bible from bible.unfoldingword.org

* Run these commands on the us.door43.org server:

    ```
    cd /var/www/vhosts/bible.unfoldingword.org/app/content/texts
    rm -rf uw_lang_ulb (or uw_* to remove and regenerate all)
    
    su unfoldingword
    cd /var/www/vhosts/bible.unfoldingword.org
    make build
    ```

* Run these commands locally:
    ```
    cd ~/Projects/uw-web && make publish
    ```
