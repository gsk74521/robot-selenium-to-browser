*** Settings ***
Library           SeleniumLibrary
Resource          common.resource

*** Variables ***
${HOME_URL}       https://example.com

*** Test Cases ***
购物流程
    [Setup]    打开首页
    登录用户    buyer01    pass123
    添加商品到购物车    SKU-1001
    校验购物车数量    1

*** Keywords ***
打开首页
    [Documentation]    打开首页并等待加载
    Open Browser    ${HOME_URL}    chrome
    Wait Until Page Contains    首页标题

登录用户
    [Documentation]    登录指定用户
    [Arguments]    ${username}    ${password}
    Input Text    id=username    ${username}
    Input Password    id=password    ${password}
    Click Button    id=login-btn
    Wait Until Element Is Visible    css=.user-avatar    10s

添加商品到购物车
    [Documentation]    将商品加入购物车
    [Arguments]    ${sku}
    Click Element    css=tr[data-sku="${sku}"] .add-btn
    Page Should Contain    已加入购物车

校验购物车数量
    [Documentation]    校验购物车徽标数量
    [Arguments]    ${expected}
    ${actual}=    Get Text    css=.cart-badge
    Should Be Equal    ${actual}    ${expected}
