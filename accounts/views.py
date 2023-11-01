import pyrebase
import firebase_admin
from firebase_admin import credentials, firestore, storage
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, HttpResponse
from .forms import ArticleForm
import os  
from datetime import timedelta, datetime
import math
from weasyprint import HTML
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.utils.translation import activate, gettext as _
from collections import defaultdict
import locale
import json
from .secrets import API_KEY, AUTH_DOMAIN, PROJECT_ID, STORAGE_BUCKET, MESSAGING_SENDER_ID, APP_ID

GTK_FOLDER = r'C:\Program Files\GTK3-Runtime Win64\bin'
os.environ['PATH'] = GTK_FOLDER + os.pathsep + os.environ.get('PATH', '')
os.add_dll_directory(r"C:\Program Files\GTK3-Runtime Win64\bin")


firebase_config = {
    "apiKey": API_KEY,
    "authDomain": AUTH_DOMAIN,
    "projectId": PROJECT_ID,
    "storageBucket": STORAGE_BUCKET,
    "messagingSenderId": MESSAGING_SENDER_ID,
    "appId": APP_ID,
    "databaseURL":"",
}
firebase = pyrebase.initialize_app(firebase_config)
# Initialize Firebase Admin SDK with your service account key JSON
cred = credentials.Certificate("secrets/serviceAccountKey.json")
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'secrets/serviceAccountKey.json'
firebase_admin.initialize_app(cred, {'storageBucket': 'bamby-8660b.appspot.com'})


def parse_firestore_date(date_str):
    # Parse the Firestore date string into a datetime object
    return datetime.strptime(date_str, '%d-%m-%Y à %H:%M:%S')

def truncate(number, digits) -> float:
    nbDecimals = len(str(number).split('.')[1]) 
    if nbDecimals <= digits:
        return number
    stepper = 10.0 ** digits
    return math.trunc(stepper * number) / stepper

def home(request):
    # Activate the French translation context
    activate('fr')
    locale.setlocale(locale.LC_TIME, 'fr_FR')
    timezone.activate('Africa/Tunis')

    current_datetime = timezone.localtime(timezone.now())
    
    # Translate the day of the week and month
    day_of_week = _(current_datetime.strftime("%A"))
    month = _(current_datetime.strftime("%B"))

    # Format the date using the translated strings
    formatted_date = {
        'hour_minute': current_datetime.strftime("%H:%M"),
        'day_of_week': day_of_week,
        'day': current_datetime.strftime("%d"),
        'month': month,
    }

    db = firestore.Client()

    # Query Firestore for the top 5 affiliates based on the "CA" field
    ca_query = db.collection('Affiliate').order_by('CA', direction=firestore.Query.DESCENDING).limit(5)
    top_ca_affiliates = ca_query.stream()

    # Convert Firestore documents to a list of dictionaries
    ca_affiliates_data = [doc.to_dict() for doc in top_ca_affiliates]

    # Calculate the start and end date of the current month
    today = datetime.now()
    start_of_month = today.replace(day=1)
    end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    # Query Firestore for the top 5 affiliates with the most orders in the current month
    orders_query = (
        db.collection('Order')
        .where('Status', '==', 'Payée')
        .stream()
    )

    # Filter orders for the current month
    current_month_orders = [
        order for order in orders_query
        if start_of_month <= parse_firestore_date(order.to_dict().get('Date')) <= end_of_month
    ]

    # Count the number of orders per affiliate
    orders_count = {}
    # Count the monthly earnings
    tht = 0
    red = 0
    for order in current_month_orders:
        tht += float(order.to_dict().get('PHT'))
        red += float(order.to_dict().get('Commission'))
        affiliate_name = order.to_dict().get('OrderBy')
        if affiliate_name in orders_count:
            orders_count[affiliate_name] += 1
        else:
            orders_count[affiliate_name] = 1
    if tht==red==0:
        earnings=0
    else:
        earnings = truncate(tht-red, 3)
    
    # Sort affiliates by the number of orders in descending order
    sorted_orders_affiliates = sorted(orders_count.items(), key=lambda x: x[1], reverse=True)[:5]

    #########
    #chart
    # Calculate the start and end date of the last 5 months
    today = datetime.now()
    end_date = today.replace(day=1)

    # Fetch the last 5 months' labels in numeric format
    last_5_months_labels = [(end_date - timedelta(days=i*30)).strftime('%m') for i in range(4, -1, -1)]

    # Query Firestore for all orders with 'Status' == 'Payée'
    all_orders_query = (
        db.collection('Order')
        .where('Status', '==', 'Payée')
        .stream()
    )

    all_orders = [order.to_dict() for order in all_orders_query]

    # Prepare data for the line chart
    monthly_order_counts = defaultdict(int)

    # Fetch all orders for each month
    for order in all_orders:
        order_date = parse_firestore_date(order.get('Date'))
        month = order_date.strftime('%m')
            
        if month in last_5_months_labels:
            monthly_order_counts[month] += 1

    # Convert data to lists for chart rendering
    chart_labels = list(monthly_order_counts.keys())
    chart_data = list(monthly_order_counts.values())
    if chart_data != [] or chart_labels!=[]:
        sorted_data = sorted(zip(chart_labels, chart_data))
        sorted_labels, sorted_data = zip(*sorted_data)

        chart_data_json = json.dumps(sorted_data)
        chart_labels_json = json.dumps(sorted_labels)
    else:
        chart_data_json = json.dumps(chart_data)
        chart_labels_json = json.dumps(chart_labels)


        # Merge existing context data with both sets of affiliate data
    context = {
            'formatted_date': formatted_date,
            'top_ca_affiliates': ca_affiliates_data,
            'top_orders_affiliates': sorted_orders_affiliates,
            'monthly_earnings': earnings,
            'chart_data_json': chart_data_json,
            'chart_labels_json': chart_labels_json,
        }

    return render(request, 'accounts/dashboard.html', context)

def orders(request):
    db = firestore.client()
    orders_collection = db.collection("Order")
    orders = orders_collection.stream()
    orders_list = []

    # Initialize counters for "en cours" and "payé" statuses
    en_cours_count = 0
    paye_count = 0

    for order in orders:
        order_data = order.to_dict()
         # Fetch articles data from the "Articles" sub-collection
        articles_collection_ref = order.reference.collection("Articles")
        articles = articles_collection_ref.stream()
        articles_data = [article.to_dict() for article in articles]
        orders_list.append({
            "AdrLivraison": order_data.get("AdrLivraison", ""),
            "Date": order_data.get("Date", ""),
            "OrdRef": order_data.get("OrdRef", ""),
            "OrderBy": order_data.get("OrderBy", ""),
            "OrderById": order_data.get("OrderById", ""),
            "TelLivraison": order_data.get("TelLivraison", ""),
            "Status": order_data.get("Status", ""),
            "PCatalog": float(order_data.get("PCatalog", 0.0)),  
            "PHT": float(order_data.get("PHT", 0.0)),
            "Commission": float(order_data.get("Commission", 0.0)),
            "PNet": float(order_data.get("PNet", 0.0)),
            "Articles": articles_data,  # Add articles data to the order 
        })
        # Count orders with "en cours" status
        if order_data.get("Status") == "En cours":
            en_cours_count += 1

        # Count orders with "payé" status
        if order_data.get("Status") == "Payée":
            paye_count += 1
    
    # Calculate the total number of orders
    total_orders = len(orders_list)
    orders_list.sort(key=lambda x: x["Date"], reverse=True)
    # Set the number of orders per page
    orders_per_page = 10  # You can adjust this as needed

    # Create a Paginator instance
    paginator = Paginator(orders_list, orders_per_page)

    # Get the current page number from the request's GET parameters
    page = request.GET.get('page')

    try:
        # Get the Page object for the requested page
        orders = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        orders = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g., 9999), deliver last page.
        orders = paginator.page(paginator.num_pages)

    context = {
        "orders": orders,
        "total_orders": total_orders,
        "en_cours_count": en_cours_count,
        "paye_count": paye_count,
    }

    return render(request, 'accounts/orders.html', context)

def search_orders(request):
    search_query = request.GET.get('search', '')
    db = firestore.client()
    orders_collection = db.collection("Order")
    orders = orders_collection.stream()
    orders_list = []
    en_cours_count = 0
    paye_count = 0

    for order in orders:
        order_data = order.to_dict()
        if search_query.lower() in order_data.get('OrderBy', '').lower() or search_query.lower() in order_data.get('OrdRef', '').lower():
            articles_collection_ref = order.reference.collection("Articles")
            articles = articles_collection_ref.stream()
            articles_data = [article.to_dict() for article in articles]
            orders_list.append({
                "AdrLivraison": order_data.get("AdrLivraison", ""),
                "Date": order_data.get("Date", ""),
                "OrdRef": order_data.get("OrdRef", ""),
                "OrderBy": order_data.get("OrderBy", ""),
                "OrderById": order_data.get("OrderById", ""),
                "TelLivraison": order_data.get("TelLivraison", ""),
                "Status": order_data.get("Status", ""),
                "PCatalog": float(order_data.get("PCatalog", 0.0)),  
                "PHT": float(order_data.get("PHT", 0.0)),
                "Commission": float(order_data.get("Commission", 0.0)),
                "PNet": float(order_data.get("PNet", 0.0)),
                "Articles": articles_data,  # Add articles data to the order 
            })
            # Count orders with "en cours" status
            if order_data.get("Status") == "En cours":
                en_cours_count += 1

            # Count orders with "payé" status
            if order_data.get("Status") == "Payée":
                paye_count += 1
    total_orders = len(orders_list)
    orders_list.sort(key=lambda x: x["Date"], reverse=True)

    
    orders_per_page = 10  # You can adjust this as needed

    # Create a Paginator instance
    paginator = Paginator(orders_list, orders_per_page)

    # Get the current page number from the request's GET parameters
    page = request.GET.get('page')

    try:
        # Get the Page object for the requested page
        orders = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        orders = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g., 9999), deliver last page.
        orders = paginator.page(paginator.num_pages)
    context = {
        "orders": orders,
        "total_orders": total_orders,
        "en_cours_count": en_cours_count,  # Add the count of "en cours" orders to the context
        "paye_count": paye_count,  # Add the count of "payé" orders to the context
        'search_query': search_query,
    }
    
    return render(request, 'accounts/orders.html', context)

def percentage(lower_level, higher_level):
    levels = {
        "Confirmé": [1],
        "Junior": [0.07],
        "Senior": [0.12, 0.06],
        "Expert": [0.15, 0.1, 0.05],
        "Leader": [0.19, 0.14, 0.08, 0.04],
        "Manager": [0.22, 0.15, 1, 0.07, 0.05],
        "Argent": [0.23, 0.16, 0.1, 0.07, 0.05],
        "Rubis": [0.26, 0.2, 0.13, 0.08, 0.05],
        "Or": [0.3, 0.24, 0.17, 0.14, 0.11],
        "Diamant": [0.27, 0.21, 0.14, 0.09, 0.06],
        "Émeraude": [0.28, 0.22, 0.15, 0.12, 0.1],
        "Saphir": [0.3, 0.24, 0.17, 0.14, 0.11],
    }
    return levels[higher_level][list(levels.keys()).index(lower_level)]

def checkCA(superior, CA):
    #we want to search aff invited by person who has id=superior except the one who has id=id 
    db = firestore.Client()
    # Define the collection reference
    affiliate_collection = db.collection('Affiliate')
    # Query documents where "Superior" field is equal to superior's id
    query = affiliate_collection.where('Superior', '==', superior)
    # Get the documents
    documents = query.stream()
    ok = True
    # Iterate through the documents and print their data
    for document in documents:
        data = document.to_dict()
        if float(data.get('CA'))>= CA*0.7:
            ok = False
            break                
    return ok

def primeAnim(id, gradei, montant, gen):
    db = firestore.client()
    affiliate_collection = db.collection("Affiliate")
    for i in range(gen):
        affiliate_doc_ref = affiliate_collection.document(id)
        affiliate_doc = affiliate_doc_ref.get()
        affiliate_data = affiliate_doc.to_dict()
        superior = affiliate_data.get("Superior")
        ca = float(affiliate_data.get("CA"))
        grades = affiliate_data.get("Grade")
        if gradei == grades:
            break
        elif checkCA(id, ca)==False:
            break
        else:
            perc = percentage(gradei, grades)
            primeAnim= truncate(montant * perc, 3)
            montant= montant-primeAnim
            affiliate_doc_ref.update({"primeAnim": firestore.Increment(truncate(primeAnim, 3))})
            affiliate_doc_ref.update({"Solde": firestore.Increment(truncate(primeAnim, 3))})
            id = superior
            gradei = grades
            if id == "6J70atZ3wiQ721ZEksqvVaCI0mg1":
                break

def CA(pc, id):
    db = firestore.client()
    affiliate_collection = db.collection("Affiliate")
    while( id != "6J70atZ3wiQ721ZEksqvVaCI0mg1"):
        affiliate_doc_ref = affiliate_collection.document(id)
        affiliate_doc = affiliate_doc_ref.get()
        affiliate_data = affiliate_doc.to_dict()
        pc= truncate(pc, 3)
        affiliate_doc_ref.update({"CA": firestore.Increment(pc)})
        id = affiliate_data.get("Superior")

def update_status(request):
    if request.method == "POST":
        ord_ref = request.POST.get("ord_ref")
        new_status = request.POST.get("new_status")
        db = firestore.client()
        orders_collection = db.collection("Order")
        order_ref = orders_collection.where("OrdRef", "==", ord_ref).limit(1).get()

        for order_doc in order_ref:
            order_doc_ref = orders_collection.document(order_doc.id)
            order_doc_ref.update({"Status": new_status})
            if new_status == "Payée":
                orders_collection = db.collection("Order")
                order_doc_ref = orders_collection.document(ord_ref)
                order_doc = order_doc_ref.get()
                order_data = order_doc.to_dict()
                order_id = order_data.get("OrderById", "")
                pht = float(order_data.get("PHT", 0.0))
                pcatalog = float(order_data.get("PCatalog", 0.0))
                réd = float(order_data.get("Commission", 0.0))
                affiliate_collection = db.collection("Affiliate")
                affiliate_doc_ref = affiliate_collection.document(order_id)
                affiliate_doc = affiliate_doc_ref.get()
                affiliate_data = affiliate_doc.to_dict()
                
                #chiffre d'affaire
                CA(pcatalog, order_id)

                superior = affiliate_data.get("Superior")
                if affiliate_data.get("firstOrder")=="true" and pcatalog>=100:
                    affiliate_doc_ref.update({"firstOrder": "false"})
                    affiliate_doc_ref.update({"Grade": "Confirmé"}) 
                    #prime de parainnage
                    affiliate_doc_ref = affiliate_collection.document(superior)
                    affiliate_doc = affiliate_doc_ref.get()
                    affiliate_data = affiliate_doc.to_dict()
                    grade = affiliate_data.get("Grade")
                    if grade=="Confirmé":
                        perc = 0.1
                    elif grade=="Junior":
                        perc = 0.17
                    elif grade=="Senior":
                        perc = 0.2
                    elif grade=="Expert":
                        perc = 0.24
                    elif grade=="Leader":
                        perc = 0.26
                    elif grade=="Manager":
                        perc = 0.3
                    else:
                        perc = 0.32
                    primeAff = truncate((pht-réd)*perc, 3)
                    affiliate_doc_ref.update({"primeAff": firestore.Increment(primeAff)})
                    affiliate_doc_ref.update({"Solde": firestore.Increment(primeAff)})
                    #Prime animation
                    superior = affiliate_data.get("Superior")
                    grade = affiliate_data.get("Grade")
                    montant= pht-réd-primeAff
                    primeAnim(superior, grade, montant, 3)
                else:
                    #Prime animation
                    grade = affiliate_data.get("Grade")
                    primeAnim(superior, grade, pht-réd, 4)
    return HttpResponseRedirect('/orders')

def search_article(request):
    search_query = request.GET.get('search', '')
    db = firestore.Client()

    # Query Firestore to get the list of articles
    articles_ref = db.collection('Articles')
    articles = articles_ref.stream()  # This retrieves all documents in the collection

    # Create a list to store article data
    article_list = []
    for article in articles:
        article_data = article.to_dict()
        if search_query.lower() in article_data.get('Ref', '').lower():
            article_list.append(article_data)

    article_per_page = 12  # You can adjust this as needed

    # Create a Paginator instance
    paginator = Paginator(article_list, article_per_page)

    # Get the current page number from the request's GET parameters
    page = request.GET.get('page')

    try:
        # Get the Page object for the requested page
        articles = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        articles = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g., 9999), deliver last page.
        articles = paginator.page(paginator.num_pages)
    # Pass the article list to the template context
    context = {'articles': articles,}

    return render(request, 'accounts/products.html', context)

def products(request):
    # Initialize Firestore client
    db = firestore.Client()

    # Query Firestore to get the list of articles
    articles_ref = db.collection('Articles')
    articles = articles_ref.stream()  # This retrieves all documents in the collection

    # Create a list to store article data
    article_list = []
    for article in articles:
        article_data = article.to_dict()
        article_list.append(article_data)

    article_per_page = 12  # You can adjust this as needed

    # Create a Paginator instance
    paginator = Paginator(article_list, article_per_page)

    # Get the current page number from the request's GET parameters
    page = request.GET.get('page')

    try:
        # Get the Page object for the requested page
        articles = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        articles = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g., 9999), deliver last page.
        articles = paginator.page(paginator.num_pages)
    # Pass the article list to the template context
    context = {'articles': articles,}

    return render(request, 'accounts/products.html', context)

def create_article(request):
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES)
        if form.is_valid():
            # Get form data
            ref = form.cleaned_data['Ref']
            prixu = float(form.cleaned_data['PrixU'])
            images = request.FILES.getlist('Images')

            couleurs = []
            # Extract the initial color (if available)
            if 'Couleur' in form.cleaned_data:
                couleurs.append(form.cleaned_data['Couleur'])
            # Extract selected colors from JSON
            
            for key, value in request.POST.items():
                if key.startswith('color_'):
                    couleurs.append(value)
            
            tailles = []
            # Extract the initial taille (if available)
            if 'Taille' in form.cleaned_data:
                tailles.append(form.cleaned_data['Taille'])
            # Extract selected tailles from JSON
            for key, value in request.POST.items():
                if key.startswith('taille_'):
                    tailles.append(value)

            ages = []
            # Extract the initial taille (if available)
            if 'Age' in form.cleaned_data:
                ages.append(form.cleaned_data['Age'])
            # Extract selected tailles from JSON
            for key, value in request.POST.items():
                if key.startswith('age_'):
                    ages.append(value)

            # Firebase Storage bucket
            bucket = storage.bucket()  # Initialize the bucket here

            # Create Firestore document for the article with "Ref" as the document ID
            db = firestore.Client()
            article_ref = db.collection('Articles').document(ref)
            article_ref.set({
                'Ref': ref,
                'PrixU': prixu,
                'PrixUHT': truncate(prixu / 1.19, 3),
                'Couleurs': couleurs,  # Store colors as an array
                'Tailles': tailles,    # Store tailles as an array
                'Ages': ages,
                'ImageUrls': []  # Initialize with an empty array
            })

            # Save images to the corresponding folder and update image URLs
            image_urls = []
            i = 0
            for image in images:
                blob = bucket.blob(f'Articles/{ref}/{str(i)}')  # Remove the leading slash here
                i += 1
                blob.upload_from_string(image.read(), content_type=image.content_type)
                # Generate a non-expiring signed URL
                image_url = blob.generate_signed_url(expiration=timedelta(days=365*1000), method="GET")  # 1 year expiration
                image_urls.append(image_url)


            # Update Firestore document with image URLs
            article_ref.update({
                'ImageUrls': image_urls
            })

            return redirect('/products')  # Redirect to a success page


    else:
        form = ArticleForm()

    return render(request, 'accounts/create_article.html', {'form': form})

def delete_document(request, ref):
    # Initialize Firestore client
    db = firestore.Client()
    # Define the reference to the Firestore document
    doc_ref = db.collection('Articles').document(ref)  # Replace 'Articles' with your collection name
    # Delete the document
    doc_ref.delete()

    bucket = storage.bucket()

    # Define the path to the folder to delete
    folder_path = f'Articles/{ref}'  # Adjust the path as needed

    # Delete the folder and its contents
    blob_list = bucket.list_blobs(prefix=folder_path)
    for blob in blob_list:
        blob.delete()

    return redirect('/products')  # Redirect to a suitable URL after deletion

def delete_order(request, ref):
    # Initialize Firestore client
    db = firestore.Client()
    # Define the reference to the Firestore document
    doc_ref = db.collection('Order').document(ref) 
    # Delete the document
    doc_ref.delete()

    return redirect('/orders')  # Redirect to a suitable URL after deletion

def delete(ref):
    # Initialize Firestore client
    db = firestore.Client()
    # Define the reference to the Firestore document
    doc_ref = db.collection('Articles').document(ref)  # Replace 'Articles' with your collection name
    # Delete the document
    doc_ref.delete()

    bucket = storage.bucket()

    # Define the path to the folder to delete
    folder_path = f'Articles/{ref}'  # Adjust the path as needed

    # Delete the folder and its contents
    blob_list = bucket.list_blobs(prefix=folder_path)
    for blob in blob_list:
        blob.delete()

def edit_article(request, ref):
    db = firestore.Client()
    doc_ref = db.collection("Articles").document(ref)
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES)
        if form.is_valid():
            delete(ref)
            prixu = float(form.cleaned_data['PrixU'])
            images = request.FILES.getlist('Images')

            couleurs = []
            # Extract the initial color (if available)
            if 'Couleur' in form.cleaned_data:
                couleurs.append(form.cleaned_data['Couleur'])
            # Extract selected colors from JSON
            
            for key, value in request.POST.items():
                if key.startswith('color_'):
                    couleurs.append(value)
            
            tailles = []
            # Extract the initial taille (if available)
            if 'Taille' in form.cleaned_data:
                tailles.append(form.cleaned_data['Taille'])
            # Extract selected tailles from JSON
            for key, value in request.POST.items():
                if key.startswith('taille_'):
                    tailles.append(value)
            
            ages = []
            # Extract the initial taille (if available)
            if 'Age' in form.cleaned_data:
                ages.append(form.cleaned_data['Age'])
            # Extract selected tailles from JSON
            for key, value in request.POST.items():
                if key.startswith('age_'):
                    ages.append(value)


            # Firebase Storage bucket
            bucket = storage.bucket()  # Initialize the bucket here

            # Create Firestore document for the article with "Ref" as the document ID
            db = firestore.Client()
            article_ref = db.collection('Articles').document(ref)
            article_ref.set({
                'Ref': ref,
                'PrixU': prixu,
                'PrixUHT': truncate(prixu / 1.19, 3),
                'Couleurs': couleurs,  # Store colors as an array
                'Tailles': tailles,    # Store tailles as an array
                'Ages': ages,
                'ImageUrls': []  # Initialize with an empty array
            })

            # Save images to the corresponding folder and update image URLs
            image_urls = []
            i = 0
            for image in images:
                blob = bucket.blob(f'Articles/{ref}/{str(i)}')  # Remove the leading slash here
                i += 1
                blob.upload_from_string(image.read(), content_type=image.content_type)
                # Generate a non-expiring signed URL
                image_url = blob.generate_signed_url(expiration=timedelta(days=365*1000), method="GET")  # 1 year expiration
                image_urls.append(image_url)


            # Update Firestore document with image URLs
            article_ref.update({
                'ImageUrls': image_urls
            })

            return redirect('/products')  # Redirect to a success page


    else:
        article_data = doc_ref.get().to_dict()
        form = ArticleForm(initial=article_data)

    return render(request, 'accounts/edit_article.html', {'form': form, 'ref': ref})

def generate_invoice(request, order_ref):
    db = firestore.Client()
    orders_collection = db.collection("Order")
    order_doc_ref = orders_collection.document(order_ref)
    order_doc = order_doc_ref.get()
    order_data = order_doc.to_dict()
    order_by = order_data.get("OrderBy", "")
    order_tel = order_data.get("TelLivraison", "")
    order_date = order_data.get("Date", "")
    order_adr = order_data.get("AdrLivraison", "")
    order_pc = order_data.get("PCatalog", "")
    order_pht = order_data.get("PHT", "")
    order_PNet = order_data.get("PNet", "")
    order_Commission = order_data.get("Commission", "")
    order_FLivraison = order_data.get("FraisLivraison", "")
    order_TVA = order_data.get("TVA", "")
    order_Timbre = order_data.get("Timbre", "")
    articles_collection_ref = order_doc_ref.collection("Articles")
    articles = articles_collection_ref.stream()
    articles_data = [article.to_dict() for article in articles]
    template_path = 'accounts/invoice.html'
    
    context = {
        'order_ref': order_ref,
        'order_by': order_by,
        'tel': order_tel,
        'order_date': order_date,
        'order_adr': order_adr,
        'order_pc': order_pc,
        'order_pht': order_pht,
        'order_PNet': order_PNet,
        'order_Commission': order_Commission,
        'order_FLivraison': order_FLivraison,
        'order_TVA': order_TVA,
        'order_Timbre': order_Timbre,
        'Articles': articles_data,
    }

    html_string = render(request, template_path, context).content.decode('utf-8')

    # Create a PDF file using weasyprint
    pdf_file = HTML(string=html_string).write_pdf()

    # Set up response to return the PDF
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'filename=invoice_{order_ref}.pdf'


    return response

def network(request):
    db = firestore.client()

    # Fetch data from Firestore
    affiliate_collection = db.collection('Affiliate')
    documents = affiliate_collection.stream()

    data_list = []
    search_query = request.GET.get('search', '')


    for document in documents:
        data = document.to_dict()

        # Check if Nom or CIN contains the search query
        if search_query.lower() in data.get('Nom', '').lower() or search_query.lower() in data.get('CIN', '').lower() or search_query.lower() in data.get('UID', '').lower():
            data_list.append(data)
    memb_per_page = 10  # You can adjust this as needed

    # Create a Paginator instance
    paginator = Paginator(data_list, memb_per_page)

    # Get the current page number from the request's GET parameters
    page = request.GET.get('page')

    try:
        # Get the Page object for the requested page
        members = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        members = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g., 9999), deliver last page.
        members = paginator.page(paginator.num_pages)
    # Pass data, search query, and a flag indicating if there are results to the template
    has_results = bool(data_list)
    return render(request, 'accounts/network.html', {'data_list': members, 'search_query': search_query, 'has_results': has_results})

def delete_Aff(request, id):
    # Initialize Firestore client
    db = firestore.Client()
    # Define the reference to the Firestore document
    doc_id = db.collection('Affiliate').document(id)  # Replace 'Articles' with your collection name
    # Delete the document
    doc_id.delete()
    return redirect('/network')

def get_children(db, superior_id):
    # Function to get children documents based on the "Superior" field
    return db.collection('Affiliate').where('Superior', '==', superior_id).stream()

def generate_tree(db, superior_id):
    # Recursively generate the HTML tree structure
    children = get_children(db, superior_id)
    
    if not children:    
        return f"<li><a href='#'>{db.collection('Affiliate').document(superior_id).get().get('Nom')}</a></li>"

    result = f"<li><a href='#'>{db.collection('Affiliate').document(superior_id).get().get('Nom')}</a><ul>"

    for child in children:
        child_id = child.id
        result += generate_tree(db, child_id)

    result += "</ul></li>"
    return result

def mlm_tree(request):
    # Assuming you have instantiated Firestore client
    db = firestore.client()

    # Starting from the person with "Superior" field equal to 1
    tree_html = generate_tree(db, '6J70atZ3wiQ721ZEksqvVaCI0mg1')

    context = {'tree_html': tree_html}
    return render(request, 'accounts/mlm_tree.html', context)
