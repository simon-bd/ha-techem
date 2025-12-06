"""Constants for Techem integration."""
DOMAIN = "techem"

CONF_COUNTRY = "country"
CONF_OBJECT_ID = "object_id"

COUNTRIES = {
    "dk": {
        "name": "Denmark",
        "url": "https://techemadmin.dk/analytics/graphql",
        "referer": "https://beboer.techemadmin.dk/"
    },
    "no": {
        "name": "Norway", 
        "url": "https://techemadmin.no/analytics/graphql",
        "referer": "https://beboer.techemadmin.no/"
    }
}
