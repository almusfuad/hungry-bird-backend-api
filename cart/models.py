from django.db import models, transaction
from hungryBird.baseModels import TimeStampedModel
from django.core.exceptions import ValidationError
from django.db.models import Q, UniqueConstraint, Sum, F, DecimalField, ExpressionWrapper
from order.models import Order, OrderItem, OrderAddOn

class Cart(TimeStampedModel):
    """
    Shopping cart for customers. Only one active cart per customer per restaurant.
    """
    customer = models.ForeignKey(
        'authUser.User', 
        on_delete=models.CASCADE, 
        related_name='carts',
        limit_choices_to={'role': 1}
    )
    restaurant = models.ForeignKey(
        'restaurant.Restaurant', 
        on_delete=models.CASCADE, 
        related_name='carts'
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields = ['customer', 'restaurant'],
                condition = Q(is_active=True),
                name = 'unique_active_cart_per_customer_per_restaurant'
            )
        ]

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


    def get_total_price(self):
        """Calculate total cart price including items and add-ons"""
        items_total = self.cart_items.aggregate(
            total = Sum(
                F("quantity") * F("menu_item__price"),
                output_field=DecimalField()
            ))["total"] or 0

        addons_total = CartAddOn.objects.filter(
                cart_item__cart=self
            ).aggregate(
                total = Sum(
                    F("quantity") * F("add_on__price"),
                    output_field=DecimalField()
                )
            )["total"] or 0
        
        return items_total + addons_total
    

    def add_item(self, menu_item, quantity):
        if menu_item.restaurant_id != self.restaurant_id:
            raise ValidationError(
                "Menu item does not belong to the cart's restaurant."
            )
        
        item, created = CartItem.objects.get_or_create(
            cart = self,
            menu_item = menu_item,
            defaults = {'quantity': quantity}
        )

        if not created:
            item.quantity += quantity
            item.save()


    def confirm(self, delivery_address):
        """
        Convert cart to order. This will:
        1. Create an Order from the cart
        2. Clone CartItems to OrderItems
        3. Clone CartAddOns to OrderAddOns
        4. Deactivate the cart
        """
        if not self.is_active:
            raise ValidationError("Cannot confirm an inactive cart.")
        if not self.cart_items.exists():
            raise ValidationError("Cannot confirm an empty cart.")
        

        with transaction.atomic():
            order = Order.objects.create(
                customer = self.customer,
                restaurant = self.restaurant,
                delivery_address = delivery_address,
                total_price = self.get_total_price()
            )

            for cart_item in self.cart_items.select_related("menu_item"):
                order_item = OrderItem.objects.create(
                    order = order,
                    menu_item = cart_item.menu_item,
                    quantity = cart_item.quantity
                )


                OrderAddOn.objects.bulk_create([
                    OrderAddOn(
                        order_item = order_item,
                        add_on = addon.add_on,
                        quantity = addon.quantity
                    )
                    for addon in cart_item.cart_add_ons.all()
                ])

            self.is_active = False
            self.save(update_fields=['is_active'])
        
        return order



    def get_items_count(self):
        """Get total number of items in cart"""
        return sum([item.quantity for item in self.cart_items.all()])

    def clear(self):
        """Empty the cart"""
        self.cart_items.all().delete()

    def __str__(self):
        return f"Cart for {self.customer.username} - {self.restaurant.name}"




class CartItem(TimeStampedModel):
    """
    Individual item in a cart
    """
    cart = models.ForeignKey(
        'cart.Cart', 
        on_delete=models.CASCADE, 
        related_name='cart_items'
    )
    menu_item = models.ForeignKey(
        'restaurant.MenuItem', 
        on_delete=models.CASCADE,
        related_name='in_carts'
    )
    quantity = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        ordering = ['created_at']
        unique_together = ('cart', 'menu_item')

    def clean(self):
        """Validate that menu item belongs to same restaurant as cart"""
        if self.menu_item.restaurant != self.cart.restaurant:
            raise ValidationError(
                "Menu item does not belong to the cart's restaurant."
            )
        if not self.menu_item.is_available:
            raise ValidationError(
                f"{self.menu_item.name} is not available."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_item_total(self):
        """Calculate total price for this item (quantity * price)"""
        return self.menu_item.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.menu_item.name} in Cart #{self.cart.id}"




class CartAddOn(TimeStampedModel):
    """
    Add-ons for items in cart
    """
    cart_item = models.ForeignKey(
        'cart.CartItem', 
        on_delete=models.CASCADE, 
        related_name='cart_add_ons'
    )
    add_on = models.ForeignKey(
        'restaurant.AddOn', 
        on_delete=models.CASCADE,
        related_name='in_carts'
    )
    quantity = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'Cart Add-On'
        verbose_name_plural = 'Cart Add-Ons'
        ordering = ['created_at']
        unique_together = ('cart_item', 'add_on')

    def clean(self):
        """Validate that add-on belongs to the same menu item"""
        if self.add_on.menu_item != self.cart_item.menu_item:
            raise ValidationError(
                "Add-on does not belong to this menu item."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_add_on_total(self):
        """Calculate total price for this add-on"""
        return self.add_on.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.add_on.name} for CartItem #{self.cart_item.id}"
