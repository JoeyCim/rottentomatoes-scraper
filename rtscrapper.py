#!/usr/bin/env python

from contextlib import closing
from bs4 import BeautifulSoup
import requests
import matplotlib.pyplot as plot
import numpy as np

HOMEPAGE = "http://www.rottentomatoes.com"
CHUNK_SIZE = 4 * 1024

def parse_selector(soup, selector):
    ''' Retrieve information about all movies under some selector '''
    
    movies = [] 

    # Store the value of the previous tag's href attribute -- helps ensure that
    # the entry being stored is legitimate
    lastHREF = ""

    for tag in soup.select(selector):
        if tag.string is None:
            continue
        if tag["href"] == lastHREF:
            continue
        if tag.string in [x["name"] for x in movies]:
            continue
        
        lastHREF = tag["href"]
        content = {}
        content["name"] = tag.string
        content["critic_score"] = tag.find_previous("span").string.strip()
        
        # We want to represent valid critic scores as ints
        if content["critic_score"][-1] == "%":
            content["critic_score"] = int(content["critic_score"][:-1])

        content.update(parse_page(HOMEPAGE + tag.get("href")))
        movies.append(content)
    return movies

def parse_homepage():
    ''' Soupify homepage and get data about opening and "top box office" 
    movies'''

    page = requests.get(HOMEPAGE)
    soup = BeautifulSoup(page.text)
    movies = []
    opening_selector = '#homepage-opening-this-week a[href*="/m/"]'
    top_box_selector = '#homepage-top-box-office a[href*="/m/"]'
  
    movies.extend(parse_selector(soup, opening_selector))
    top_box_movies = parse_selector(soup, top_box_selector)
    #movies.extend(top_box_movies)

    # Ensure no duplicates. Not a particularly efficient way to deal with this,
    # but the movie list is generally no more than 10-15 items long, so it's
    # not a very big deal
    for movie in top_box_movies:
        if movie["name"] not in [mov["name"] for mov in movies]:
            movies.append(movie)
            
    return movies

def parse_page(page_url):
    '''Get audience approval data from a movie's webpage'''

    additional_content = {}

    # requests.get(...) is the main bottleneck here.
    # Streaming it and using the iter_content generator shaves
    # off a few seconds.
    with closing(requests.get(page_url,stream = True)) as page:
        for chunk in page.iter_content(CHUNK_SIZE):
            soup = BeautifulSoup(chunk)
            audience_review_tag = soup.select('[name="twitter:data2]')
            if audience_review_tag != []:
                audience_review = audience_review_tag[0].get("content")

                # If the audience has reviewed this movie, represent the review 
                # as an int containing the audience's percent
                # approval.
                perc_index = audience_review.find("%")
                if perc_index != -1:
                    audience_review = int(audience_review[:perc_index])
                additional_content["audience_review"] = audience_review
                break
    return additional_content


def print_row(item):
    '''Prints a row of data containing a particular movie's data. '''

    print("{0:<25}{1:<25}{2:<25}".format(item[0],item[1],item[2]))

def sort_data(movie_list, sort_key):
    '''Sort data according to a particular criteria'''

    # Move all entries from movie_list into filtered_list if they don't have
    # data for the given sort_key
    filtered_list = []
    
    if sort_key == "critic_score":
        filtered_list = [x for x in movie_list if 
                type(x["critic_score"]) is unicode]
    elif sort_key == "audience_review":
        filtered_list = [x for x in movie_list if type(x["audience_review"]) 
            is unicode and "want" in x["audience_review"]] 
    elif sort_key == "audience_anticipation":
        filtered_list =  [x for x in movie_list if type(x["audience_review"])
            is unicode and "liked" in x["audience_review"]]
    movie_list = [x for x in movie_list if x not in filtered_list]
   
    if sort_key == "audience_anticipation": #Still sort the second row
        sort_key = "audience_review"

    filtered_list.sort(key= lambda k: k[sort_key], reverse=True)
    movie_list.sort(key= lambda k: k[sort_key], reverse=True)
    movie_list += filtered_list
    return movie_list

def print_data(data):
    print_row(["Movie name: ","Critic score: ", "Audience score"])
    print("")

    for movie in data:
        print_row([shorten(movie['name'], 22),movie['critic_score'],
            movie['audience_review']])

def shorten(name, length):
    if (len(name) <= length):
        return name
    else:
        return name[:length-3] + "..."

def create_plot(data):
    critic_scores = tuple([x['critic_score'] for x in data if 
        isinstance(x['critic_score'], int)])
    
    # Ensure that an audience/critic score pair are only graphed if both
    # have valid values
    audience_scores = tuple([x['audience_review'] for x in data if
        isinstance(x['audience_review'], int) and
        x['critic_score'] in critic_scores]) 
    critic_scores = tuple([x['critic_score'] for x in data if 
        x['critic_score'] in critic_scores and
        x['audience_review'] in audience_scores])
    movie_names = tuple([shorten(x['name'], 10) for x in data if
        x['critic_score'] in critic_scores])
    movie_count = len(critic_scores)

    index = np.arange(0, movie_count * 2, 2)
    bar_width = 0.35

    critic_bars = plot.bar(index, critic_scores, bar_width,
                     color='b',
                     label = 'Critic')
    audience_bars = plot.bar(index + bar_width, audience_scores, bar_width,
                     color='r',
                     label = 'Audience')
 
    plot.xlabel('Movie Names')
    plot.ylabel('Percent Approval')
    plot.title('Critic and Audience Ratings of Various Movies')
    plot.xticks(index + bar_width, movie_names)
    plot.legend()

    plot.tight_layout()
    plot.show()

def main():
    print("\nFetching data...")
    results = parse_homepage()
    print("Data loaded\n")
    
    while True:
        print("AUDIENCE: Sort by audience ratings, "
              "CRITIC: Sort by critic ratings, \n" 
              "ANTICIPATION: Sort by audience anticipation, "
              "PLOT: Generate a plot of current data, "
              "QUIT: Exit")
        choice = raw_input("Your selection: ")
        print("")
        
        if choice.upper() == "AUDIENCE":
            results = sort_data(results, "audience_review")
            print_data(results)
        elif choice.upper() == "CRITIC":
            results = sort_data(results, "critic_score")
            print_data(results)
        elif choice.upper() == "ANTICIPATION":
            results = sort_data(results, "audience_anticipation")
            print_data(results)
        elif choice.upper() == "PLOT":
            create_plot(results)
        elif choice.upper() == "QUIT":
            break;
        else:
            print("Invalid choice.")
        print("")

if __name__ == "__main__":
    main()
