import random
import spotipy
import spoticonfig
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
import numpy as np

#connect to spotify
cid =spoticonfig.Client_ID
secret =spoticonfig.Client_Secret
rurl =spoticonfig.redirect_uri

sp= spotipy.Spotify(auth_manager=spotipy.SpotifyOAuth(client_id=cid,client_secret=secret,redirect_uri=rurl))

#get playlist id and convert
pre_playlist1=(input("Enter the first playlists URL: "))
pre_playlist2=(input("Enter the second playlists URL: "))

def playlist_url_seperator(playlist):
 playlist=playlist.removeprefix('https://open.spotify.com/playlist/')
 playlist=playlist.split('?si=', 1)[0] 
 pl_id = 'spotify:playlist:'+playlist
 return pl_id

playlist1=playlist_url_seperator(pre_playlist1)
playlist2=playlist_url_seperator(pre_playlist2)

#get name of playlists
def get_name_of_playlist(playlist):
    name=sp.playlist(playlist_id=playlist,fields="name")
    return name.get("name")
playlist1_name=get_name_of_playlist(playlist1)
playlist2_name=get_name_of_playlist(playlist2)

#get track info of playlists
def get_track_id_pop_exp_artist(playlist_id):
 results = sp.playlist_tracks(playlist_id,fields="next,items.track.name,items.track.id,items.track.artists.id,items.track.explicit,items.track.popularity")
 playlist = results['items']
 while results['next']:
    results = sp.next(results)
 playlist.extend(results['items']) 

 thelist=[]  
 for i in playlist:
        thelist.append(i)        
 for d in thelist:
     d.update(d.pop('track', {}))
     
 song_in_playlist = pd.DataFrame(thelist)
 return(song_in_playlist)


playlist1_tracks=get_track_id_pop_exp_artist(playlist1)
playlist2_tracks=get_track_id_pop_exp_artist(playlist2)

playlist1_tracks_list=playlist1_tracks["id"].tolist()
playlist2_tracks_list=playlist2_tracks["id"].tolist()

lenght_of_playlist1=len(playlist1_tracks)
lenght_of_playlist2=len(playlist2_tracks)

#track number control
if (lenght_of_playlist1 or lenght_of_playlist2)<5:
    print("Playlist requried at least 5 tracks.")
    
#create dataframe with audio_features
def true_false_mapper(val):
    if val==True:
        return 1
    elif val==False:
        return 0
    
def get_audio_features_playlist(playlist_tracks,lenght):
 track_list = playlist_tracks["id"].values.tolist()
 explicit_list = playlist_tracks["explicit"].values.tolist()
 explicit_list=next(map(true_false_mapper, explicit_list))  # maping list transform(True,False) to (1,0)
 popularity_list = playlist_tracks["popularity"].values.tolist()
 artists_list = playlist_tracks["artists"].values.tolist() 

 if lenght>100:
  p=divmod(lenght,100)
  counter=0   
  while counter!=p[0]+1:  
   x=counter*100
   if x+100<lenght:
    y=x+100
   else:
    y=lenght
   if counter==0:
    af=sp.audio_features(track_list[x:y])
    af=pd.DataFrame(af)
    counter=counter+1
   else:
    temp=sp.audio_features(track_list[x:y])
    temp=pd.DataFrame(temp)
    af=pd.concat([af,temp],axis=0)
    counter=counter+1
 else:
   af=sp.audio_features(track_list)
   af=pd.DataFrame(af)
 af.pop('analysis_url')
 af.pop('track_href')
 af.pop('type')
 af.pop('uri') 
 af["explicit"]=explicit_list  
 af["popularity"]=popularity_list
 af["artists"]=artists_list
 return (af)

df_playlist1=get_audio_features_playlist(playlist1_tracks,lenght_of_playlist1)
df_playlist2=get_audio_features_playlist(playlist2_tracks,lenght_of_playlist2)

print("Analyzing song features...")
# find common audio_features of each playlists

def std_avg_of_features(df_playlist): #danceability,energy,mode,speechiness,acousticness,instrumentalness,liveness,valance,explicit,popularity
 df_temp=df_playlist
 df_temp=df_temp.drop(columns=["key","loudness","id","duration_ms","time_signature","artists","explicit","tempo","mode","speechiness"])
 df_temp["popularity"]=df_temp["popularity"]/100
 std=df_temp.std()
 avg=df_temp.mean()
 df=pd.concat([std, avg], axis=1,)
 result = df.rename(columns={df.columns[0]: 'std',df.columns[1]: 'mean'})
 result["lower_bound"]=result["mean"]-result["std"]
 result["upper_bound"]=result["mean"]+result["std"]
 
 return result
# create filter for better recommendation
lower_bound_list=[]
upper_bound_list=[]
p1_df=std_avg_of_features(df_playlist1)
p2_df=std_avg_of_features(df_playlist2)

for i in range(7):
    temp=[]
    temp.append(p1_df.iloc[i][2])
    temp.append(p2_df.iloc[i][2])
    lower_bound_list.append(max(temp))
    temp.clear()
    
    temp2=[]
    temp2.append(p1_df.iloc[i][3])
    temp2.append(p2_df.iloc[i][3])
    upper_bound_list.append(min(temp2))
    temp2.clear()
    
data = {'upper_bound':upper_bound_list,
        'lower_bound':lower_bound_list,}
  
filter = pd.DataFrame(data, index =["danceability","energy","acousticness","instrumentalness","liveness","valence","popularity"])
conditions = [((filter["upper_bound"]-filter["lower_bound"])<0.1),
              ((filter["upper_bound"]-filter["lower_bound"])>=0.1)]
values = [0, 1]
filter["isvalid"]=np.select(conditions, values)

# find similar song/artist in playlists
def common_song_finder(playlist1,playlist2):
 songs1=playlist1["id"].tolist()
 songs2=playlist2["id"].tolist()
 same_songs=list(set(songs1).intersection(songs2))
 return same_songs
def common_artist_finder(playlist1,playlist2):
 artist1=playlist1["artists"].tolist()
 artist2=playlist2["artists"].tolist()
 artist_ids_1=[]
 artist_ids_2=[]
 
 for i in artist1:
    artist_ids_1.append(i[0].get("id"))
 for i in artist2:
    artist_ids_2.append(i[0].get("id"))
 same_artists=list(set(artist_ids_1).intersection(artist_ids_2))
 return same_artists

# find 5 common track/artist or pick random nad recoomend

same_songs=common_song_finder(df_playlist1,df_playlist2)
same_artists=common_artist_finder(df_playlist1,df_playlist2)

def randomlist(playlist1,playlist2):
 randlst=[]
 weight = random.randint(1,2) 
 if weight == 1: 
  randlst= (random.sample(playlist1_tracks_list, 3)) +(random.sample(playlist2_tracks_list, 2))
 elif weight == 2:  
  randlst= (random.sample(playlist1_tracks_list, 2)) +(random.sample(playlist2_tracks_list, 3))
 return randlst

print("Generating playlist...")

def reccomend_playlist():
 songlist=[]
 artistlist=[]
 
 if len(same_songs)>5:
  songlist=random.sample(same_songs, 5)
  
 elif len(same_songs)==5:
  songlist=same_songs
 elif len(same_songs)<5 and len(same_songs)>0 :
  songlist=same_songs
  a=5-int(len(same_songs))
  if len(same_artists)==a:
   artistlist=same_artists
  elif len(same_artists)>a:
   artistlist=same_artists[:a-1]
  elif len(same_artists)<a:
     artistlist=same_artists
     songlist=songlist+randomlist(df_playlist1,df_playlist2)[:a-1]
    
 elif len(same_songs)==0:
     songlist=randomlist(df_playlist1,df_playlist2)
    
    
    
#adding filter parametersi If filter range too tight ignore that parameter
 max_acousticness=filter["upper_bound"]["acousticness"]if filter["isvalid"]["acousticness"] ==True else None
 min_acousticness=filter["lower_bound"]["acousticness"]if filter["isvalid"]["acousticness"] ==True else None
 max_danceability=filter["upper_bound"]["danceability"]if filter["isvalid"]["danceability"] ==True else None
 min_danceability=filter["lower_bound"]["danceability"]if filter["isvalid"]["danceability"] ==True else None
 max_energy=filter["upper_bound"]["energy"]if filter["isvalid"]["energy"] ==True else None
 min_energy=filter["lower_bound"]["energy"]if filter["isvalid"]["energy"] ==True else None
 max_instrumentalness=filter["upper_bound"]["instrumentalness"]if filter["isvalid"]["instrumentalness"] ==True else None
 min_instrumentalness=filter["lower_bound"]["instrumentalness"]if filter["isvalid"]["instrumentalness"] ==True else None
 max_liveness=filter["upper_bound"]["liveness"]if filter["isvalid"]["liveness"] ==True else None
 min_liveness=filter["lower_bound"]["liveness"]if filter["isvalid"]["liveness"] ==True else None
 max_valence=filter["upper_bound"]["valence"]if filter["isvalid"]["valence"] ==True else None
 min_valence=filter["lower_bound"]["valence"]if filter["isvalid"]["valence"] ==True else None
 max_popularity=int(100*(filter["upper_bound"]["popularity"]))if filter["isvalid"]["popularity"] ==True else None
 min_popularity=int(100*(filter["lower_bound"]["popularity"]))if filter["isvalid"]["popularity"] ==True else None
  
  
 rec=sp.recommendations(seed_tracks=songlist,seed_artists=artistlist
                        ,max_acousticness=max_acousticness
                        ,min_acousticness=min_acousticness
                        ,max_danceability=max_danceability
                        ,min_danceability=min_danceability
                        ,max_energy=max_energy
                        ,min_energy=min_energy
                        ,max_instrumentalness=max_instrumentalness
                        ,min_instrumentalness=min_instrumentalness
                        ,max_liveness=max_liveness
                        ,min_liveness=min_liveness
                        ,max_popularity=max_popularity
                        ,min_popularity=min_popularity
                        ,max_valence=max_valence
                        ,min_valence=min_valence)
 reclist=[]
 for i in rec["tracks"]:
    reclist.append(i) 
 for d in reclist:
     d.update(d.pop('tracks', {}))

 song_in_playlist = pd.DataFrame(reclist)
 result=song_in_playlist["id"].tolist()
 return result

final_song_id_list=[]
final_song_id_list=reccomend_playlist()#this is final list of songs



# creating playlist
sp= spotipy.Spotify(auth_manager=spotipy.SpotifyOAuth(client_id=cid,client_secret=secret,redirect_uri=rurl,scope='playlist-modify-public,user-read-private'))
usernameid=sp.current_user()
playlistname= str(playlist1_name)+" x "+str(playlist2_name)

#descriptions
if len(same_songs)>=10:
 description="Congrats !!!  Both playlists have a lot of songs in common"+"Playlist"+"Created by Kağan Kalafat's bot"
elif len(same_songs)<10 and len(same_songs)>=5:
 description="Both playlists have a couple of similar songs."+"Created by Kağan Kalafat's bot"
elif len(same_songs)<5 and len(same_songs)>0 :
 description="Both playlists contain some common artists."+"Created by Kağan Kalafat's bot"
else:
 description="Neither playlist contains any collaborative artists or songs."+"Created by Kağan Kalafat's bot"
 
#add song into new playlist
playlists = sp.user_playlist_create(usernameid["id"],playlistname,description=description)
sp.user_playlist_add_tracks(usernameid["id"], playlists['id'],final_song_id_list)
print("Playlist succesfuly created !")


 
 

    
    
 



    

