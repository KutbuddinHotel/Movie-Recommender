from flask import Flask, render_template, request
import pickle
import requests
from dotenv import load_dotenv
import os
from difflib import get_close_matches

app = Flask(__name__)

load_dotenv()
API_KEY = os.getenv("TMDB_API_KEY")

import requests
import os

API_KEY = os.getenv("TMDB_API_KEY")

def fetch_movie_data(movie_id):

    movie_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}"
    movie_data = requests.get(movie_url).json()

    credits_url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={API_KEY}"
    credits_data = requests.get(credits_url).json()
    
    cast = [cast["name"] for cast in credits_data["cast"][:5]]
    
    director = next((crew["name"] for crew in credits_data["crew"] 
                     if crew["job"] == "Director"),"Unknown")

    return {"poster": "https://image.tmdb.org/t/p/w500" + movie_data["poster_path"] if movie_data["poster_path"] else None,
            "title" : movie_data["title"],
            "rating": round(movie_data["vote_average"], 1),
            "runtime": movie_data["runtime"],
            "overview": movie_data["overview"],
            "release_year": movie_data["release_date"][:4],
            "genres": [genre["name"] for genre in movie_data["genres"]],
            "director": director,
            "cast": cast}


popular_movies = pickle.load(open("popular_movies.pkl", "rb"))
popular_movies["genres"] = popular_movies["movie_id"].apply(lambda movie_id: fetch_movie_data(movie_id)["genres"])
popular_movies = popular_movies.to_dict(orient="records")

new_df = pickle.load(open("new_df.pkl", "rb"))

similarity = pickle.load(open("similarity_SBERT.pkl", "rb"))


@app.route("/", methods= ["GET", "POST"])
def index(): 
    if request.method == "POST":
        movie = request.form["movie"].strip()
        matched = new_df[new_df["title"].str.lower() == movie.lower()]
            
        if matched.empty:
            suggestion = get_close_matches(movie, new_df["title"], n=10, cutoff=0.6)

            suggestion = list(dict.fromkeys(suggestion))

            suggestion = suggestion[:5]

            if suggestion:

                return render_template("index.html", popular_movies=popular_movies, suggestion=suggestion)

            return render_template("index.html", popular_movies=popular_movies, error="Movie not found.")
    
        movie_index = matched.index[0]

        similar_items = sorted(list(enumerate(similarity[movie_index])), key = lambda x: x[1], reverse=True)[1:6] 

        recommendations = [] 
    
        for el in similar_items: 
            movie_data = fetch_movie_data(new_df.iloc[el[0]].movie_id)
            recommendations.append({
                "title": new_df.iloc[el[0]].title,
                "movie_id": new_df.iloc[el[0]].movie_id,
                "genres": movie_data["genres"],
                "poster": movie_data["poster"]})
            
        return render_template("index.html", recommendations=recommendations, popular_movies=popular_movies)
    
    return render_template("index.html", popular_movies=popular_movies)


@app.route("/movie/<int:movie_id>")
def movie_details(movie_id):
    
    movie = fetch_movie_data(movie_id)
    
    return render_template("movie.html", movie=movie)


@app.route("/about")
def about():
    return render_template("about.html")

if __name__ == "__main__": 
    app.run(debug=True)