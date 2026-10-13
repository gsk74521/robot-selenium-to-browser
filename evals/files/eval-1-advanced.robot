*** Settings ***
Library           SeleniumLibrary
Suite Setup       Open Browser    https://example.com    chrome    options=add_argument("--headless")
Suite Teardown    Close All Browsers

*** Variables ***
${FRAME_BTN}      //div[@id='panel']/button
${ROW_SEL}        css=.data-row

*** Test Cases ***
弹出确认框并处理
    Click Element    id=delete-btn
    Handle Alert    accept
    Alert Should Be Present

iframe 内点击
    Select Frame    id=main-frame
    Click Element    id=inner-btn
    Unselect Frame

执行 JS 滚动
    Execute Javascript    window.scrollTo(0, 500)
    ${count}=    Execute Javascript    return document.querySelectorAll('.row').length;

元素句柄复用
    ${elem}=    Get WebElement    ${ROW_SEL}
    Click Element    ${elem}
    ${attr}=    Get Element Attribute    ${ROW_SEL}    data-id

隐式等待配置
    Set Selenium Implicit Wait    5
    Maximize Browser Window
    ${loc}=    Get Location

前置定位策略
    Click Element    name=submit
    Click Element    //button[@type='submit']
    Click Element    jquery=.special
