# -*- coding: utf-8 -*-
"""
Created on Fri Aug  7 21:29:08 2020
This is website scraper module. Call this from main to extract info from online tournaments

@author: zhafi
"""
import pandas as pd
import requests
import excel_module as em
import stat_helper as sh
from deckmodule import Deck
from bs4 import BeautifulSoup as bs



def SVO_initial_scraper(svoexcel):
    em.excel_convert_quick(svoexcel, 'Sheet1')
    em.excel_convert_dataset(svoexcel, 3)
    em.excel_statistics('Excel_and_CSV/FilteredDecks_Data.xlsx', 3)
    em.combine_view_and_stats()

#JCG scraper
# 1. Retrieve jsonlink and create excel sheet that contains Name, Deck1, and Deck2 (JCG_Raw.xlsx)
# 2. Based on that, it will create FilteredDecks_View, FilteredDecks_Data, and Statistics
# input example 'https://sv.j-cg.com/compe/view/entrylist/2341/json'
def JCG_scraper(jsonlink):
    jcglink = jsonlink
    response = requests.get(jcglink)
    data1 = response.json()
    data2 = pd.DataFrame(list(data1['participants']))
    data3 = data2.loc[data2['te'] == 1] # Only filter those who checked in
    data4 = pd.DataFrame(list(data3['dk'])).rename(columns={0:'deck 1',1:'deck 2'}) #Grab df from column dk, then rename it properly
    data5 = data3['nm'].reset_index().drop(['index'], axis=1) #create a series with name only
    data6 = pd.concat([data5, data4], axis=1) #combine name and deck1,deck2
    
    #JCG deck syntax Handling
    sv = 'https://shadowverse-portal.com/deck/'
    lang_eng = '?lang=en'
    data6 = data6.rename(columns={'nm':'name'})
    data6['deck 1'] = data6['deck 1'].apply(lambda x: x['hs'] if x else None)
    data6['deck 1'] = data6['deck 1'].apply(lambda x: sv + x + lang_eng if x else 'Invalid Deck')
    data6['deck 2'] = data6['deck 2'].apply(lambda x: x['hs'] if x else '')
    data6['deck 2'] = data6['deck 2'].apply(lambda x: sv + x + lang_eng if x else 'Invalid Deck')
    
    writer = pd.ExcelWriter('Excel_and_CSV/JCG_Raw.xlsx')
    data6.to_excel(writer)
    writer.save()
    
    em.excel_convert_quick('Excel_and_CSV/JCG_Raw.xlsx', 'Sheet1')
    em.excel_convert_dataset('Excel_and_CSV/JCG_Raw.xlsx', 2)
    em.excel_statistics('Excel_and_CSV/FilteredDecks_Data.xlsx', 2)
    em.combine_view_and_stats()

#Scrap data from MS Gaming in Battlefy
#requirements : Json link : //tournaments/..../teams . Can be found in response at Participants tab
#input example https://dtmwra1jsgyb0.cloudfront.net/tournaments/5f1e79da534e897bd0c64673/teams 
def manasurge_bfy_scraper(jsonlink):
    response = requests.get(jsonlink)        
    data = response.json()
    
    # Grab Dataframe, decklist were located in another dictionary inside customFields
    # expand Customfields by temp df, then merge them to orginal df
    df1 = pd.DataFrame(data)
    df2 = pd.DataFrame(list(df1['customFields']))
    df2['name'] = df1['name']
    df = df1.merge(df2)
    
    # Decklist were in column 2 , 3 , and 4 (Different tournament may use different fields)
    # Decklist were inside another dictionary. Use nested for loop to obtain actual decklist and update our df
    df = df[['name',2,3,4]]
    total_participants = df.shape[0] 
    for i in range(2,5):
        for j in range(0,total_participants):
            df[i][j] = df[i][j]['value']
    
    df = df.rename(columns={2:'deck 1', 3:'deck 2', 4:'deck 3'})
    
    writer = pd.ExcelWriter('Excel_and_CSV/MS_Raw.xlsx')
    df.to_excel(writer)
    writer.save()
        
    em.excel_convert_quick('Excel_and_CSV/MS_Raw.xlsx', 'Sheet1')
    em.excel_convert_dataset('Excel_and_CSV/MS_Raw.xlsx', 3)
    em.excel_statistics('Excel_and_CSV/FilteredDecks_Data.xlsx', 3)
    em.combine_view_and_stats()
    
    
# Read quick stats from top performers
# Prerequisite : SVO_initial_scraper must be run first. FilteredDecks_Data should contain all participants
# Input : latest-round-standings json ex: 'https://dtmwra1jsgyb0.cloudfront.net/stages/5f1266601047db149e9edf9e/latest-round-standings'
def SVO_tops_scraper_v1(jsonlink):
    svolink = jsonlink
    response = requests.get(svolink)        
    data = response.json()
    df1 = pd.DataFrame(data)
    df2 = pd.DataFrame(list(df1['team'])).rename(columns={'_id':'teamID'})
    df = df1.merge(df2, on='teamID')
    df = df[['name', 'wins','losses','disqualified']]
    df = df.loc[(df['wins']>2) & (df['losses']<3) & (df['disqualified']== False)]
    
    alldata = pd.read_excel("Excel_and_CSV/FilteredDecks_Data.xlsx")
    dfdata = df.merge(alldata, on='name')
    dfview = dfdata[['name', 'wins','losses','arc 1','arc 2','arc 3']]
    
    writer = pd.ExcelWriter('Excel_and_CSV/SVOTopCut_Data.xlsx')
    dfdata.to_excel(writer, 'Data')
    dfview.to_excel(writer, 'View')
    writer.save()
    
    em.excel_statistics('Excel_and_CSV/SVOTopCut_Data.xlsx', 3)
    

def SVO_posttourney_scraper(tourneyhash , stagehash):
    # # We are dealing with 3 data frame
    # # dfa = overall dataframe from filtered data
    # # dfb = dataframe that acquired from matches.json. Contains all information about matches and results
    # # dfc = dataframe that acquired from teams.json. Contains all information about players, especially teamID and name
    

    dfa = pd.read_excel('Excel_and_CSV/FilteredDecks_Data.xlsx') 
    
    # Obtain matches and removes 'byes' or any invalid matched that doesnt contain statistics data
    matchjson = 'https://dtmwra1jsgyb0.cloudfront.net/stages/'+ stagehash + '/matches'
    response = requests.get(matchjson)        
    data = response.json()
    
    dfb = pd.DataFrame(data)
    dfb = dfb.fillna(0)
    dfb = dfb.loc[dfb['stats']!=0].reset_index()
    
    # Obtain teamID and name from json. Then, create a python dictionary based on that.
    playerjson = 'https://dtmwra1jsgyb0.cloudfront.net/tournaments/' + tourneyhash + '/teams'
    response2 = requests.get(playerjson)        
    data2 = response2.json()
    
    dfc = pd.DataFrame(data2)
    dfc = dfc[['_id', 'name']].rename(columns={'_id':'teamID'})
    dfc = dfc.set_index('teamID')
    playerdict = dfc.to_dict() 
    
    #Obtain win-loss swiss record from standings
    standingsjson = 'https://dtmwra1jsgyb0.cloudfront.net/stages/' + stagehash + '/latest-round-standings'
    response3 = requests.get(standingsjson)        
    data3 = response3.json()
    
    # add swiss-win-loss into alldf
    df1 = pd.DataFrame(data3)
    df2 = pd.DataFrame(list(df1['team'])).rename(columns={'_id':'teamID'})
    df = df1.merge(df2, on='teamID')
    # df = df.loc[(df['wins']>2) & (df['losses']<3) & (df['disqualified']== False)]
    df = df[['name', 'wins','losses']]
    alldf = dfa.merge(df, on='name')
    
    # Scrap info about Wins, Loss, Bans
    alldf = sh.get_ban_data(alldf, dfb, dfc)
    alldf = sh.get_win_loss_data(alldf, dfb, dfc, playerdict)
    
    # Create string for that contains W / L / B
    for i in range(1,4):
        alldf[f'deck {i} W/L/B'] = alldf[f'win {i}'].apply(int).apply(str) + '/' + alldf[f'loss {i}'].apply(int).apply(str) + '/' + alldf[f'ban {i}'].apply(int).apply(str)
    
    #export cleaned data for View
    alldf_view = alldf[['name', 'wins','deck 1', 'deck 2', 'deck 3', 'deck 1 W/L/B', 'deck 2 W/L/B', 'deck 3 W/L/B']].sort_values(by='wins', ascending=False)
    alldf_view = alldf_view.reset_index().drop(['index'], axis=1).set_index(['name'])
    
    #Calculate Win-Ban Archetype Ratio
    winbanstats = sh.get_win_ban_archetype(alldf)
    
    
    writer = pd.ExcelWriter('Excel_and_CSV/Post_SVO_Data.xlsx')
    alldf_view.to_excel(writer, 'Sheet1')
    winbanstats.to_excel(writer, 'Archetype Stats')
    writer.save()
    
    # convert svoportal link to archetype name
    em.excel_convert_quick('Excel_and_CSV/Post_SVO_Data.xlsx', 'Sheet1', True)
        
    
# url = 'https://sv.j-cg.com/compe/2373'
# source = requests.get(url).text
# soup = bs(source, 'lxml')

# winners = soup.find_all('p', class_="rank rank-1")
# winnerlist = []
# for win in winners:
#     name = win.findNext().text
#     winnerlist.append(name)
# namedf = pd.DataFrame(winnerlist).rename(columns={0:'name'})

# df = pd.read_excel('Excel_and_CSV/FilteredDecks_View.xlsx')
# fdf = df.merge(namedf)
# decks = fdf.loc[:,'deck 1':'deck 2'].stack().value_counts(normalize = False, ascending = False)
# decks = decks.rename_axis("Deck Archetype").reset_index(name = 'Count')
    
# player = 'TK Zy'
# tourneyhash = '5f02c761bf38ff0aa1f90bcf'
# stagehash = '5f37504d6ce6de28d63dd645'

def SVO_ban_peek(player, tourneyhash, stagehash):
    
    dfa = pd.read_excel('Excel_and_CSV/FilteredDecks_Data.xlsx') 
        
    # Obtain matches and removes 'byes' or any invalid matched that doesnt contain statistics data
    matchjson = 'https://dtmwra1jsgyb0.cloudfront.net/stages/'+ stagehash + '/matches'
    response = requests.get(matchjson)        
    data = response.json()
    
    dfb = pd.DataFrame(data)
    dfb = dfb.fillna(0)
    dfb = dfb.loc[dfb['stats']!=0].reset_index()
    
    # Obtain teamID and name from json. Then, create a python dictionary based on that.
    playerjson = 'https://dtmwra1jsgyb0.cloudfront.net/tournaments/' + tourneyhash + '/teams'
    response2 = requests.get(playerjson)        
    data2 = response2.json()
    
    dfc = pd.DataFrame(data2)
    dfc = dfc[['_id', 'name']].rename(columns={'_id':'teamID'})
    dfc = dfc.set_index('teamID')
    playerdict = dfc.to_dict() 
    
    dfb['top teamID'] = dfb.loc[:,'top'].apply(lambda x: x['teamID'])
    dfb['bot teamID'] = dfb.loc[:,'bottom'].apply(lambda x: x['teamID'])
    dfb['player 1'] = dfb.loc[:,'top teamID'].apply(lambda x: playerdict['name'][x])
    dfb['player 2'] = dfb.loc[:,'bot teamID'].apply(lambda x: playerdict['name'][x])
    dfb['player 1 banned'] = dfb.loc[:,'top'].apply(lambda x: x.get('bannedClass', 'none') )
    dfb['player 2 banned'] = dfb.loc[:,'bottom'].apply(lambda x: x.get('bannedClass', 'none'))
    
    # Quick Class View
    dfview = dfb.copy()
    dfview = dfview[['player 1', 'player 1 banned', 'player 2 banned', 'player 2']]
    
    dictionary = dfa[['name','class 1','class 2','class 3','arc 1','arc 2','arc 3']].copy()
    dictionary.astype({'name':'str'})
    for i in range (1,4):
        dictionary[f'nameclass{i}'] = dictionary['name'] + dictionary[f'class {i}']
        
    nameclass = dictionary.loc[:,'nameclass1':'nameclass3'].stack().reset_index().rename(columns={0:'nameclass'})
    arche = dictionary.loc[:,'arc 1':'arc 3'].stack().reset_index().rename(columns={0:'archetype'})
    diction = pd.concat([nameclass, arche], axis=1)
    diction = diction[['nameclass','archetype']].set_index('nameclass')
    pa_dict = diction.to_dict()
    
    dffinal = dfview.copy()
    dffinal['playerarc1'] = dffinal['player 1']+ dffinal['player 1 banned']
    dffinal['playerarc2'] = dffinal['player 2']+ dffinal['player 2 banned']
    dffinal['Banned 1'] = dffinal.loc[:,'playerarc1'].apply(lambda x: pa_dict.get('archetype').get(x, 'Unknown Unknown'))
    dffinal['Banned 2'] = dffinal.loc[:,'playerarc2'].apply(lambda x: pa_dict.get('archetype').get(x, 'Unknown Unknown'))
    
    dffinal = dffinal[['player 1', 'Banned 1', 'Banned 2', 'player 2']]
    
    search = dffinal[(dffinal['player 1']==f'{player}') | (dffinal['player 2']==f'{player}')]
    
    return search


# df = pd.read_excel('Excel_and_CSV/FilteredDecks_Data.xlsx')
# df = df[['name','arc 1', 'arc 2']]

# url = 'https://sv.j-cg.com/compe/view/tour/2334'
# source = requests.get(url).text
# soup = bs(source, 'lxml')

# winnerlist = []
# winleft = soup.find_all('li', class_="tour_match left winner")

# for win in winleft:
#     name = win.findNext().findNext().text
#     winnerlist.append(name)

# winright = soup.find_all('li', class_="tour_match right winner")
# for win in winright:
#     name = win.findNext().findNext().text
#     winnerlist.append(name)

# windf = pd.DataFrame(winnerlist).rename(columns={0:'name'})

# loserlist = []
# loseleft = soup.find_all('li', class_="tour_match left")
# for lose in loseleft:
#     name = lose.findNext().findNext().text
#     loserlist.append(name)
    
# loseright = soup.find_all('li', class_="tour_match right")
# for lose in loseright:
#     name = lose.findNext().findNext().text
#     loserlist.append(name)

# lossdf = pd.DataFrame(loserlist).rename(columns={0:'name'})

# win = df.merge(windf, how='inner', on='name')
# wintotal = win.loc[:,'arc 1':'arc 2'].stack().value_counts(normalize = False, ascending = False)
# wintotal = wintotal.rename_axis("Deck Archetype").reset_index(name = 'WinTotal')


# loss = df.merge(lossdf, how='inner', on='name')
# losstotal = loss.loc[:,'arc 1':'arc 2'].stack().value_counts(normalize = False, ascending = False)
# losstotal = losstotal.rename_axis("Deck Archetype").reset_index(name = 'LossTotal')

# summary = wintotal[['Deck Archetype','WinTotal']]
# summary['LossTotal'] = losstotal['LossTotal']
# summary['Winrate'] = summary['WinTotal']/(summary['WinTotal'] + summary['LossTotal'])






