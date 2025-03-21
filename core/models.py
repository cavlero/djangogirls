from django.db import models

class Recipe(models.Model):
    recipe_title = models.TextField(blank=True, null=True)
    nyt_recipe_id = models.BigIntegerField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    recipe_yield = models.TextField(blank=True, null=True)
    total_time = models.TextField(blank=True, null=True)
    steps = models.TextField(blank=True, null=True)
    rating = models.TextField(blank=True, null=True)   #This field type is a guess.
    author = models.TextField(blank=True, null=True)
    image = models.TextField(blank=True, null=True)
    tags = models.TextField(blank=True, null=True)
    ingredients_full = models.TextField(blank=True, null=True)
    id = models.BigIntegerField(blank=True, null=False, primary_key=True)

    class Meta:
        managed = False
        db_table = 'recipe_data'