import requests
import json

url = 'https://resdex.naukri.com/cloudgateway-resdex/recruiter-js-profile-listing-services/v0/rdxLite/search'

headers = {
    'accept': 'application/json',
    'accept-language': 'en-US,en;q=0.9',
    'appid': '112',
    'content-type': 'application/json',
    'origin': 'https://resdex.naukri.com',
    'priority': 'u=1, i',
    'referer': 'https://resdex.naukri.com/lite/candidatesearchresults?requirementId=130761&requirementGroupId=130761&showFeedbackWidget=true&resPerPage=50&pageNo=1&activeTab=potential&accessedResPerPage=50&accessedPageNo=1&sid=2544149&sidGroupId=9bf3a8aa49cf313926414d636f54ca06&totalResumes=500',
    'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'systemid': 'naukriIndia',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
    # 'x-transaction-id': 'rlsrp14472963774479147711557776619531~~e4f63b', # Using static for test
    # Cookie from user provided cURL
    'cookie': 'geo_country=IN; J=0; ninjas_new_marketing_token=133bc1f856fc7fd49fe2f5a09c43dd4d; _clck=zawyd3%5E2%5Eg1r%5E0%5E2171; ph_phc_s4aJa5RpiiZlHbbxy4Y1Btjhosozg9ECrSuJNVrvZuP_posthog=%7B%22distinct_id%22%3A%2219b0da8da0ae22-0427dee075f8978-1c525631-1ce26a-19b0da8da0b212a%22%7D; _ga_7TYVEWTVRG=GS2.1.s1765460728$o1$g1$t1765460779$j9$l0$h0; _ga_JCSR1LRE3X=GS2.1.s1765460728$o1$g1$t1765460779$j9$l0$h0; _fbp=fb.1.1765463042285.648062430113477467; test=naukri.com; _t_r=1030%2F%2F; persona=default; _did=aac7000fa8; _odur=1b6e71d851; UNPC=125281556; UNCC=125666042; loginPreference=null_null; _ga_T749QGK6MQ=GS2.1.s1765463430$o1$g1$t1765463550$j54$l0$h0; logout_check=1; _t_ds=3147e901765469139-113147e90-03147e90; lastLoggedInUser=krrish@grrbaow.com; cart_125666042={"resdexWithOffer":["4196"]}; kycEligibleCookie125281556=false; dashboard=1; encId=fcb94ecce0ac4d2e2d9f4916dd971037595f0c574c150915016; _gid=GA1.2.961916702.1765613072; __gads=ID=c99bdcea1ec68b8c:T=1765460739:RT=1765615360:S=ALNI_MZhejrplW4VAVKQqi3-6nm2WBRZNQ; __gpi=UID=000011c80db7c023:T=1765460739:RT=1765615360:S=ALNI_MaZ8rOqd6_DsdXOjxb90Brglrvd9A; __eoi=ID=61b6a06dbf3f814c:T=1765460739:RT=1765615360:S=AA-AfjayATCB7VFEr0j4YiTmAArw; _gcl_gs=2.1.k1$i1765693141$u93512962; _gcl_aw=GCL.1765693144.Cj0KCQiAuvTJBhCwARIsAL6DemgR-BsE0hLACXgGGHQu9lh8wp6QVUCZvwXYGtoCi0FQDJEDhVRK1gMaAg75EALw_wcB; _gcl_dc=GCL.1765693144.Cj0KCQiAuvTJBhCwARIsAL6DemgR-BsE0hLACXgGGHQu9lh8wp6QVUCZvwXYGtoCi0FQDJEDhVRK1gMaAg75EALw_wcB; lite_idx_page_pref=litejavares; SnippedURL=https%3A%2F%2Frecruit.naukri.com%2F; bs_rnd=Eb15912E; ak_bmsc=B2877F9C4CCB553DEC85B48345F4B0EC~000000000000000000000000000000~YAAQRPTfF1/xkv2aAQAAtw1VIB63o2hGXk4P3/bK38gGQsRb5kWM4vB0rImJAHSNptxBwGkd9Yt+IXAPplPiy+NkgJVaI7UlSw61c7gjk0TTDnoY0kee4jOtCgEajfY/GyFOHBzEkahc8ABtOnZuzhHJOIOkqJ/F5nXfXdOkjJGtL3IkzsEbbbYNENuMUREGf7ZvFPGoqo39j+CVUTl7tFCpSwpDkUqBek6ER+7CVQmujaAzwRuHscSvlRmNwvvE4Skse+cpIOYb7TL/stadw40EaSP2yGfFSDwpW51nDk8f4/P8RmsoFwNu5Ebw4BfFS3asRZTn5LQ5vqAmzq2KfzU4sxOo1IMvTpFSA7/A+7KlO6W786oevnU9p41EFGFveo39eoLHq/ddzXb+quCH1DsjwE5KYoOrzccg72QWuVsjbUCoFNpa4jUULrMWqm8g0TqbsyOL9pSIVkb2Bbd33b9a9/sOhq4vYXUw4JpcknwEdn7NeZPWyA==; 9af2d37fe018023139dbf2c153f72ab11s7=v0%7CHEhw2sJpdqrIl3ZME3jPuX0gBk6531%2BEDNNe2lK5vidoWu0E3J9jw8LPk4qnTZuS3eEBU3iPtHvJGuLnL1cpPy%2FfVlbnYITdFwbuTtjOaELsQ0Ld8KuXcRAuDqSxnX7Ji2P3NwlOg57rEg1kJlJPJUYZBtyJ5gkMKAYV4bUfgRI%3D; _gcl_au=1.1.1130093136.1765463042.1323227642.1765774005.1765774016; pvId=0; ACCESS=1765774017436; UNID=gMS2DBNdV8udrHwuBN3swhnY6cHarbOsfB3GrUfI; _ga_K2YBNZVRLL=GS2.1.s1765774003$o13$g1$t1765774017$j46$l0$h0; _ga=GA1.2.31587001.1765460729; HOWTORT=ul=1765776619241&r=https%3A%2F%2Fresdex.naukri.com%2Flite%2Fcandidatesearchresults%3FrequirementId%3D130761%26requirementGroupId%3D130761%26showFeedbackWidget%3Dtrue%26resPerPage%3D50%26pageNo%3D1%26activeTab%3Dpotential%26accessedResPerPage%3D50%26accessedPageNo%3D1%26sid%3D2544149%26sidGroupId%3D9bf3a8aa49cf313926414d636f54ca06%26totalResumes%3D500&hd=1765776619511; bm_sv=754CC1BC3DFAF35EE55DE5E23E855237~YAAQBfY3F7oFvqiaAQAA1A59IB5YVZp/iARcLZQ+gOYeDlyvFQJQeWcQoYdydNr90LtTY6bRtDmqi1qQJgY0iJ8xyK6+RilCzkf65sBmbVD3iQlLeOsRcp9+czhQ+sum2LGHyuOSV5azuJZ/rBSwPDnBycbwRwF+ZAmTxmH6r4AgwEmvXh/XjwUAV87MheCKcqNkW0x4SsRjnwC94JAHkw/adXnLwJX/ZlDa5llI9EY/5wPNA48P2XM9wJJN4qT6UQ==~1'
}

data = {
    "requirementId": "130761",
    "newCandidatesSearch": False,
    "saveSession": True,
    "requirementGroupId": "130761",
    "miscellaneousInfo": {
        "companyId": 125281556,
        "rdxUserId": "125666042",
        "rdxUserName": "krrish@grrbaow.com"
    }
}

print(f"Testing URL: {url}")
try:
    response = requests.post(url, headers=headers, json=data, timeout=30)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")
