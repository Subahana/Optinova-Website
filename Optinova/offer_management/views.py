from django.shortcuts import render, redirect, get_object_or_404
from .models import CategoryOffer
from .forms import CategoryOfferForm
from django.contrib import messages


def create_category_offer(request):
    if request.method == 'POST':
        form = CategoryOfferForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category offer created successfully.")
            return redirect('offer_list')  # Adjust 'offer_list' to your correct URL name
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CategoryOfferForm()
    return render(request, 'offer/create_category_offer.html', {'form': form})

# Update a Category Offer
def update_category_offer(request, offer_id):
    offer = get_object_or_404(CategoryOffer, id=offer_id)
    if request.method == 'POST':
        form = CategoryOfferForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()
            messages.success(request, "Category offer updated successfully!")
            return redirect('offer_list')
    else:
        form = CategoryOfferForm(instance=offer)
    return render(request, 'offer/update_category_offer.html', {'form': form})

# List all Category Offers
def offer_list(request):
    offers = CategoryOffer.objects.all()
    return render(request, 'offer/category_offer_list.html', {'offers': offers})



def offer_status(request, offer_id):
    offer = get_object_or_404(CategoryOffer, id=offer_id)
    offer.is_active = not offer.is_active  # Toggle the current status
    offer.save()
    status = "activated" if offer.is_active else "deactivated"
    messages.success(request, f"The offer has been {status}.")
    return redirect('offer_list')  # Redirect to the offers list or another relevant page