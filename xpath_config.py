"""
XPATH配置文件
用于集中管理所有XPATH路径
修改XPATH时只需要在此文件中更新对应的值
"""

class XPathConfig:
    # 1.登录相关，长期有效
    LOGIN_BUTTON = [
        '//button[contains(text(), "Log In")]'
    ]
    
    # 2.Buy按钮长期有效
    BUY_BUTTON = [
        '//button[(text()="Buy")]'
    ]

    # 3.Buy Yes 按钮长期有效
    BUY_YES_BUTTON = [
        '//button[.//span[contains(text(), "Up")] and .//span[contains(text(), "¢")]]',
        '//button[.//span[contains(text(), "Yes")] and .//span[contains(text(), "¢")]]'
    ]

    # 4.Buy No 按钮长期有效
    BUY_NO_BUTTON = [
        '//button[.//span[contains(text(), "Down")] and .//span[contains(text(), "¢")]]',
        '//button[.//span[contains(text(), "No")] and .//span[contains(text(), "¢")]]'
    ]

    # 5.Sell Yes 按钮长期有效
    SELL_YES_BUTTON = [
        '//button[.//span[contains(text(), "Up")] and .//span[contains(text(), "¢")]]',
        '//button[.//span[contains(text(), "Yes")] and .//span[contains(text(), "¢")]]' 
    ]

    # 6.Sell No 按钮长期有效
    SELL_NO_BUTTON = [
        '//button[.//span[contains(text(), "Down")] and .//span[contains(text(), "¢")]]',
        '//button[.//span[contains(text(), "No")] and .//span[contains(text(), "¢")]]'   
    ]

    # 7.Buy-确认买入按钮
    BUY_CONFIRM_BUTTON = [
        '//button[@class="c-bDcLpV c-bDcLpV-fLyPyt-color-blue c-bDcLpV-ileGDsu-css"]',
        '(//*[normalize-space(.)="Max"]/ancestor::div/following-sibling::div//button)[3]'
        ]

    # 8.Sell-卖出按钮
    SELL_CONFIRM_BUTTON = [
        '//button[@class="c-bDcLpV c-bDcLpV-fLyPyt-color-blue c-bDcLpV-ileGDsu-css"]',
        '(//*[normalize-space(.)="Max"]/ancestor::div/following-sibling::div//button)[3]'
        ]

    # 9.Amount输入框长期有效
    AMOUNT_INPUT = [
        '//input[@id="market-order-amount-input"]',
        '(//*[normalize-space(.)="Amount"]/ancestor::*[2]//input)[1]'  
        ]

    # 10.Position-Up标签长期有效
    POSITION_UP_LABEL = [
        '(//*[normalize-space(.)="Positions"]/ancestor::*[1]//*[text()="Up"])[1]'
        ]

    # 11.Position-Down标签长期有效
    POSITION_DOWN_LABEL = [
        '(//*[normalize-space(.)="Positions"]/ancestor::*[1]//*[text()="Down"])[1]'
        ]

    # 14.Position-Sell按钮长期有效
    POSITION_SELL_BUTTON = [
        '(//div//h3[contains(text(),"Positions")]/ancestor::div//div/button[contains(text(),"Sell")])[1]'    
    ]

    # 15.Position-Sell Yes按钮 长期有效
    POSITION_SELL_YES_BUTTON = [
        '(//*[normalize-space(.)="Positions"]/ancestor::*[1]//div[(contains(., "Up") or contains(., "Down"))]//button[normalize-space(.)="Sell"])[1]'
        ]

    # 16.Position-Sell No按钮长期有效
    POSITION_SELL_NO_BUTTON = [
        '(//*[normalize-space(.)="Positions"]/ancestor::*[1]//div[(contains(., "Up") or contains(., "Down"))]//button[normalize-space(.)="Sell"])[2]'
        ]

    # 17.Portfolio值长期有效
    PORTFOLIO_VALUE = [
        '//a[@href="/portfolio"]//div//p[contains(text(), "$")]'
    ]

    # 18.Cash值长期有效
    CASH_VALUE = [
        '//a[@href="/portfolio"]//button//p[contains(text(), "$")]',
        '//button[.//p[text()="Cash"]]/p[contains(text(), "$")]'
    ]

    # 19.History-交易记录长期有效
    HISTORY = [
        '//h3[contains(., "History")]/parent::div/following-sibling::div[1]',
        '(//div[@class="PJLV PJLV-ihovmxi-css"])[1]',
        '(//div[@class="PJLV PJLV-ihovmxi-css"]//p)[1]' 
    ]
    
    # 20. login_with_google_button长期有效
    LOGIN_WITH_GOOGLE_BUTTON = [
        '//*[@id="authentication-modal"]/div/div[2]/div/div/div/div/button'
    ]
    
    # 21.accept_button长期有效
    ACCEPT_BUTTON = [
        '//button[contains(text(), "Accept")]',
        '//button[contains(text(), "I Accept")]'
    ]    

    # 22.定位 SPREAD 的 XPATH
    SPREAD = [
        '(//span[@class="c-ggujGL"])[2]',
        '//span[contains(text(), "Spread") or contains(text(), "spread")]'
    ]

    # 23.搜索框长期有效
    SEARCH_INPUT = [
        '//input[@id="homepage-search-input"]',
        '/html/body/div[1]/div[2]/div/div/main/div/div/div[3]/div/div/div/div[1]/div[2]/div[2]/input'
    ] 

    # 24.search_confirm_button长期有效
    SEARCH_CONFIRM_BUTTON = [
        '//p[contains(text(), "Up or Down on")]', 
        '//a//p[contains(text(), "Up or Down on")]' 
    ]

    # 25.搜索框长期有效
    SPREAD_ELEMENT = [
        '(//*[contains(text(), "Spread")])[2]/ancestor::div[3]/div[contains(., "¢")]'
    ] 

    # 26.Portfolio 按钮
    PORTFOLIO_BUTTON = [
        '//a[@href="/portfolio" and .//p[contains(text(), "Portfolio")]]'
    ]

    # 27.CLAIM 按钮
    CLAIM_BUTTON = [
        '//button[contains(text(), "Claim")]'
    ]

    # 28.DAILY_BUTTON
    DAILY_BUTTON = [
        '//div[@role="button" and .//p[text()="Daily"]]'
    ]

    # 29.CLAIM_CONFIRM_BUTTON
    CLAIM_CONFIRM_BUTTON = [
        '//button[contains(text(), "Confirm")]'
    ]

    # 30. portfolio_sell_button
    PORTFOLIO_SELL_BUTTON = [
        '//button[contains(text(), "Sell")]'
    ]

    # 31. CRYPTO_BUTTON
    CRYPTO_BUTTON = [
        '//a[@href="/crypto"]'
    ]

    # 32.search_BTC_button长期有效
    SEARCH_BTC_BUTTON = [
        '//p[contains(text(), "Bitcoin Up or Down on")]', 
        '//a//p[contains(text(), "Bitcoin Up or Down on")]' 
    ]

    # 33.search_ETH_button长期有效
    SEARCH_ETH_BUTTON = [
        '//p[contains(text(), "Ethereum Up or Down on")]', 
        '//a//p[contains(text(), "Ethereum Up or Down on")]' 
    ]

    # 34.search_SOL_button长期有效
    SEARCH_SOL_BUTTON = [
        '//p[contains(text(), "Solana Up or Down on")]', 
        '//a//p[contains(text(), "Solana Up or Down on")]' 
    ]

    # 35.UP 价格
    UP_PRICE = [
        '//button[.//span[contains(text(), "Up")]]//span[contains(text(), "¢")]'
    ]

    # 36.DOWN 价格
    DOWN_PRICE = [
        '//button[.//span[contains(text(), "Down")]]//span[contains(text(), "¢")]'
    ]