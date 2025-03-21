from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from django.db.models import Count
from django.http import FileResponse
from django.urls import reverse
import os
from .forms import SearchForm
from .models import Recipe
from ultralytics import YOLO
import cv2
from PIL import Image
import io
from django.core.paginator import Paginator
from django.db.models import F, Case, When, Value, IntegerField

# Create your views here.
def index(request):
    # Recipe count + number of predictions for dynamic numbers on index page
    recipe_amt = Recipe.objects.count()

    # Construct absolute path
    detect_path = os.path.join(default_storage.location, 'detect')

    # Ensure the path exists before listing files
    if os.path.exists(detect_path):
        predictions = len([name for name in os.listdir(detect_path) if os.path.isfile(os.path.join(detect_path, name))])
    else:
        predictions = 0  # If folder doesn't exist, set predictions to 0

    return render(request, 'index.html', {'title': 'Home', 'recipe_amt': recipe_amt, 'predictions': predictions})


# Dictionary to map numbers (int) to class names, based on .yaml file from YOLO model
class_mapping = {
    0: 'apple',1: 'avocado',2: 'carrot',3: 'cauliflower',4: 'celery',5: 'chili pepper',6: 'corn',7: 'cucumber',8: 'eggplant',9: 'garlic',
    10: 'ginger',11: 'grapes',12: 'banana',13: 'kiwi',14: 'lemon',15: 'lettuce',16: 'lime',17: 'mango',18: 'onion',19: 'orange',20: 'pear',
    21: 'pineapple',22: 'pomegranate',23: 'beet',24: 'potato',25: 'pumpkin',26: 'radish',27: 'raspberry',28: 'spinach',29: 'spring onion',
    30: 'strawberry',31: 'sweet potato',32: 'tomato',33: 'watermelon',34: 'bell pepper',35: 'zucchini',36: 'blackberry',37: 'blueberry',
    38: 'broccoli',39: 'brussels sprout',40: 'cabbage'}

def demo(request):
    filler_classes = ['bell pepper', 'bell pepper', 'apple', 'tomato', 'apple', 'bell pepper', 'tomato', 'tomato']
    filler_conf_scores = [91, 84, 81, 76, 68, 59, 55, 46]
    
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        file_extension = uploaded_file.name.rsplit('.', 1)[1].lower()
        file_path = default_storage.save(f'uploads/{uploaded_file.name}', ContentFile(uploaded_file.read()))
        file_path = os.path.join(default_storage.location, file_path)
        
        if file_extension == 'png':
            with Image.open(file_path) as img:
                jpg_filepath = file_path.rsplit('.', 1)[0] + '.jpg'
                img.convert('RGB').save(jpg_filepath)
                file_path = jpg_filepath
        
        img = cv2.imread(file_path)
        frame = cv2.imencode('.jpg', cv2.UMat(img))[1].tobytes()
        image = Image.open(io.BytesIO(frame))
        
        model_path = os.path.join(settings.BASE_DIR, 'best.pt')
        model = YOLO(model_path)
        results = model(image, save=True, conf=0.4)
        
        conf_scores = [int(round(tensor.item() * 100)) for tensor in results[0].boxes.data[:, 4]]
        classes = [class_mapping.get(int(tensor.item()), 'unknown') for tensor in results[0].boxes.data[:, 5]]
        unique_classes = ', '.join(set(classes))
        
        preprocess = int(round(results[0].speed['preprocess'], 0))
        inference = int(round(results[0].speed['inference'], 0))
        postprocess = int(round(results[0].speed['postprocess'], 0))
        
        folder_path = os.path.join(default_storage.location, 'detect')
        files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        latest_img = max(files, key=lambda x: os.path.getctime(os.path.join(folder_path, x)))
        
        return render(request, 'demo.html', {
            'filename': latest_img,
            'conf_scores': conf_scores,
            'classes': classes,
            'output_len': len(classes),
            'zipped_data' : zip(classes, conf_scores),
            'inf_time': inference,
            'pre_time': preprocess,
            'pos_time': postprocess,
            'range_vals' : range(len(classes)),
            'unique_classes': unique_classes,
        })
    
    return render(request, 'demo.html', {
        'filename': None,
        'conf_scores': filler_conf_scores,
        'classes': filler_classes,
        'output_len': len(filler_classes),
        'zipped_data' : zip(filler_classes, filler_conf_scores),
        'range_vals' : range(len(filler_classes)),
        'inf_time': None,
        'pre_time': None,
        'pos_time': None,
        'unique_classes': ', '.join(set(filler_classes)),
        
    })

def get_image(request, filename):
    """ Serves image with inference for display on demo page """
    
    # Define the path to your images directory
    image_path = os.path.join(settings.BASE_DIR, 'runs/detect', filename)
    
    # Check if the file exists
    if os.path.exists(image_path):
        return FileResponse(open(image_path, 'rb'), content_type='image/jpeg')
    else:
        # Handle the case where the image is not found
        return render(request, '404.html')  # You can create a custom 404 page if needed
    
    
def search(request):
    """ Search form which can handle multiple searches separated by a comma """
    
    form = SearchForm(request.GET)
    page = request.GET.get('page', 1)
    per_page = 10

    results = None
    prev_url = None
    next_url = None
    matching_ingredients_counts = []
    
    if form.is_valid():
        search_term = form.cleaned_data.get('search', '')
        directed_query = request.GET.get('q', None)
        
        if directed_query and not search_term:
            # Split the query string by comma
            ingredients = [ingredient.strip() for ingredient in directed_query.split(',')]
            
            # Case conditions for matching ingredients
            case_conditions = [Case(When(ingredients_full__icontains=ingredient, then=Value(1)), default=Value(0), output_field=IntegerField()) for ingredient in ingredients]
            
            # Construct the query
            queryset = Recipe.objects.all()
            
            # Add a case expression to sum matches
            queryset = queryset.annotate(matching_count=sum(case_conditions))
            
            # Filter for matching ingredients
            queryset = queryset = queryset.filter(matching_count__gt=0)
            
            queryset = queryset.order_by('-matching_count')  
            # Pagination
            paginator = Paginator(queryset, per_page)
            results = paginator.get_page(page)

            # Pagination URLs
            if results.has_next():
                next_url = f'?page={results.next_page_number()}&q={directed_query}'
            if results.has_previous():
                prev_url = f'?page={results.previous_page_number()}&q={directed_query}'

            # Count of ingredients matched for each recipe
            for recipe in results:
                matching_count = sum(ingredient in recipe.ingredients_full for ingredient in ingredients)
                matching_ingredients_counts.append(matching_count)
    else:
        print("FORM INVALID")
    print("RESULTS", results)
    print(type(results))

    print("MATCHING COUNTS", matching_ingredients_counts)
    return render(request, 'search.html', {
        'form': form,
        'query': directed_query,
        'results': results,
        'prev_url': prev_url,
        'next_url': next_url,
        'matching_ingredients_counts': matching_ingredients_counts
    })

def submit_search(request):
    """ Handle search form submission and redirect to the search page with the query """
    if request.method == "POST":
        form = SearchForm(request.POST)
        if form.is_valid():
            search_query = form.cleaned_data['search']
            return redirect(f'{reverse("search")}?q={search_query}')
    return redirect('search')

def about(request):
    """About page with a list of classes."""
    
    class_list = [
        "Apple", "Avocado", "Banana", "Beet", "Bell Pepper", "Blackberry", "Blueberry", "Broccoli", "Brussels Sprout", 
        "Cabbage", "Carrot", "Cauliflower", "Celery", "Chili Pepper", "Corn", "Cucumber", "Eggplant", "Garlic", 
        "Ginger", "Grapes", "Kiwi", "Lemon", "Lettuce", "Lime", "Mango", "Onion", "Orange", "Pear", "Pineapple", 
        "Pomegranate", "Potato", "Pumpkin", "Radish", "Raspberry", "Spinach", "Spring Onion", "Strawberry",
        "Sweet Potato", "Tomato", "Watermelon", "Zucchini"
    ]
    
    return render(request, 'about.html', {'class_list': class_list})

def show_recipe(request, search_id):
    """ Display a recipe based on search_id and render it with its details. """
    
    # Retrieve the selected recipe or return 404 if not found
    selected_recipe = get_object_or_404(Recipe, id=search_id)
    
    # Split steps and ingredients if they are available
    steps_list = selected_recipe.steps.split('____') if selected_recipe.steps else []
    ingredients_list = selected_recipe.ingredients_full.split('____') if selected_recipe.ingredients_full else []
    
    # Query all recipes for recommended recipes (optional - can limit if needed)
    recipes = Recipe.objects.all()
    print("STEPS", steps_list)
    # Render the template with recipe details
    return render(request, "recipe_single.html", {
        'recipe': selected_recipe,
        'steps_list': steps_list,
        'ingredients_list': ingredients_list,
        'recipes': recipes
    })

