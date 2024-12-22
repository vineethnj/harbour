from django.shortcuts import render
from .models import Order,Fish,Customer
# Create your views here.
from django.contrib.auth.decorators import login_required
from django.db.models import Sum



@login_required
def index(request):
    order=Order.objects.all().count()
    total_kg_sum = Fish.objects.aggregate(total_kg_sum=Sum('total_kg'))['total_kg_sum']
    customers=Customer.objects.all().count()
    context={
        'order':order,
        'fish':total_kg_sum,
        'customers':customers
    }
    return render(request,'index.html',context)



from django.shortcuts import render, redirect, get_object_or_404
from .forms import FishForm
from django.urls import reverse
from rest_framework import generics
from .serializers import FishSerializer

# List all fishes
@login_required
def fish_list(request):
    fishes = Fish.objects.all()
    return render(request, 'products.html', {'fishes': fishes})


from rest_framework.permissions import AllowAny

class FishListAPIView(generics.ListAPIView):
    queryset = Fish.objects.all()
    serializer_class = FishSerializer
    permission_classes = [AllowAny]

# Add a new fish
@login_required
def fish_create(request):
    if request.method == 'POST':
        form = FishForm(request.POST, request.FILES)
        print(form)
        if form.is_valid():
            form.save()
            return redirect('fish_list')
    return redirect('fish_list')  # Redirect to the list page in case of errors

# Edit an existing fish
@login_required
def fish_edit(request, pk):
    fish = get_object_or_404(Fish, pk=pk)
    if request.method == 'POST':
        form = FishForm(request.POST, request.FILES, instance=fish)
        if form.is_valid():
            form.save()
            return redirect('fish_list')
    return redirect('fish_list')

# Delete a fish
@login_required
def fish_delete(request, pk):
    fish = get_object_or_404(Fish, pk=pk)
    if request.method == 'POST':
        fish.delete()
        return redirect('fish_list')
    return redirect('fish_list')

@login_required
def order_list(request):
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'order_list.html', {'orders': orders})


from rest_framework.permissions import AllowAny
from rest_framework.decorators import permission_classes
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .serializers import OrderSerializer
from decimal import Decimal
@api_view(['POST'])
@permission_classes([AllowAny])

def create_order(request):
    serializer = OrderSerializer(data=request.data)

    if serializer.is_valid():
        fish_id = serializer.validated_data['fish'].id
        quantity = serializer.validated_data['quantity']
        
        try:
            fish = Fish.objects.get(id=fish_id)

            # Validate requested quantity
            if quantity <= 0:
                return Response({"error": "Quantity must be greater than zero."}, status=status.HTTP_400_BAD_REQUEST)
            
            if float(fish.total_kg) < float(quantity):
                return Response({"error": "Not enough stock available."}, status=status.HTTP_400_BAD_REQUEST)

            # Calculate total price
            total_price = float(fish.price_per_kg) * float(quantity)

            with transaction.atomic():
                # Deduct quantity from stock
                fish.total_kg = float(fish.total_kg) - float(quantity)
                fish.save()

                # Create order
                order = serializer.save(total_price=total_price)
            
            # Return response
            return Response({
                "id": order.id,
                "fish": order.fish.name,
                "quantity": order.quantity,
                "total_price": order.total_price,
                "status": order.status,
            }, status=status.HTTP_201_CREATED)

        except Fish.DoesNotExist:
            return Response({"error": "Fish not found."}, status=status.HTTP_400_BAD_REQUEST)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from .serializers import CustomerRegistrationSerializer, CustomerLoginSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Customer
@api_view(['POST'])
def register_customer(request):
    serializer = CustomerRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        customer = serializer.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(customer)
        tokens = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

        return Response({
            'message': 'Registration successful',
            'customer': {
                'id': customer.id,
                'full_name': customer.full_name,
                'phone': customer.phone,
            },
            'tokens': tokens
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def login_customer(request):
    serializer = CustomerLoginSerializer(data=request.data)
    if serializer.is_valid():
        customer = Customer.objects.get(phone=serializer.validated_data['phone'])
        
        # Generate tokens
        refresh = RefreshToken.for_user(customer)
        tokens = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

        return Response({
            'message': 'Login successful',
            'customer': {
                'id': customer.id,
                'full_name': customer.full_name,
                'phone': customer.phone,
            },
            'tokens': tokens
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



# Add an endpoint to get orders for a specific customer
@api_view(['GET'])
@permission_classes([AllowAny])
def get_customer_orders(request, customer_id):
    try:
        orders = Order.objects.filter(id=customer_id)
        
        order_data = []
        for order in orders:
            order_data.append({
                'id': order.id,
                'fish_name': order.fish.name,
                'quantity': order.quantity,
                'total_price': order.total_price,
                'status': order.status,
                'created_at': order.created_at
            })
            
        return Response(order_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )

def customersList(request):
    customers=Customer.objects.all()
    return render(request,'customers_list.html',{'customers':customers})




from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from .forms import CustomUserCreationForm, LoginForm


def register_view(request):
    if request.method == "POST":
        print(request.POST)
        form = CustomUserCreationForm(request.POST)
        print(form)
        if form.is_valid():
            user = form.save(commit=False)
            print('user:',user)
            user.is_business = True
            user.save()
            login(request, user)
            messages.success(request, f"{user} Registration successful!")
            return redirect("index")
        else:
            messages.error(request, form.errors)
    else:
        form = CustomUserCreationForm()
    return render(request, "register.html", {"form": form})



from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponseRedirect
from django.conf import settings
from django.utils import timezone

@csrf_protect
@never_cache
def login_view(request):
    # Redirect if user is already authenticated
    if request.user.is_authenticated:
        if request.user.is_business:
            return redirect("index")
        

    form = LoginForm(request.POST or None)
    print("Form errors:", form.errors) 
    print(form)
    
    if request.method == "POST":
        print("POST data:", request.POST)
        
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            
            user = authenticate(username=username, password=password)
            print(user)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    
                    # Configure session settings
                    request.session.set_expiry(settings.SESSION_COOKIE_AGE)
                    request.session['last_activity'] = str(timezone.now())
                    
                    messages.success(request, "Logged in Successfully")
                    
                    # Redirect based on user type
                    if user.is_business:
                        return redirect("index")
                    
                else:
                    messages.error(request, "Account is disabled")
            else:
                messages.error(request, "Invalid username or password")
    
    return render(request, "login.html", {"form": form})

@never_cache
def logout_view(request):
    if request.user.is_authenticated:
        # Store the logout message before clearing the session
        messages.success(request, "Logged out successfully")
        
        # Logout the user
        logout(request)
        
        # Clear all session data
        request.session.flush()
        
        # Clear any potential session cookies
        response = HttpResponseRedirect('/accounts/login/')
        response.delete_cookie(settings.SESSION_COOKIE_NAME)
        
        # Set strict no-cache headers
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        return response
    
    return redirect('login')

from rest_framework.views import APIView
from .models import Address
from .serializers import AddressSerializer

class AddressAPI(APIView):
    # Get all addresses for a customer
    def get(self, request, user_id):
        try:
            addresses = Address.objects.filter(customer_id=user_id)
            serializer = AddressSerializer(addresses, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    # Create new address
    def post(self, request, user_id):
        try:
            customer = Customer.objects.get(id=user_id)
            serializer = AddressSerializer(data=request.data)
            
            if serializer.is_valid():
                serializer.save(customer=customer)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Customer.DoesNotExist:
            return Response(
                {"error": "Customer not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

class AddressDetailAPI(APIView):
    # Get single address
    def get(self, request, user_id, address_id):
        try:
            address = Address.objects.get(customer_id=user_id, id=address_id)
            serializer = AddressSerializer(address)
            return Response(serializer.data)
        except Address.DoesNotExist:
            return Response(
                {"error": "Address not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

    # Update address
    def put(self, request, user_id, address_id):
        try:
            address = Address.objects.get(customer_id=user_id, id=address_id)
            serializer = AddressSerializer(address, data=request.data, partial=True)
            
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Address.DoesNotExist:
            return Response(
                {"error": "Address not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

    # Delete address
    def delete(self, request, user_id, address_id):
        try:
            address = Address.objects.get(customer_id=user_id, id=address_id)
            address.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Address.DoesNotExist:
            return Response(
                {"error": "Address not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

class SetDefaultAddressAPI(APIView):
    def post(self, request, user_id, address_id):
        try:
            address = Address.objects.get(customer_id=user_id, id=address_id)
            address.is_default = True
            address.save()
            serializer = AddressSerializer(address)
            return Response(serializer.data)
        except Address.DoesNotExist:
            return Response(
                {"error": "Address not found"}, 
                status=status.HTTP_404_NOT_FOUND)