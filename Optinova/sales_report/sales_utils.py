from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
from django.http import HttpResponse

def generate_invoice(order):
    # Create a BytesIO buffer to hold the PDF
    buffer = BytesIO()

    # Create a canvas object for PDF generation
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter  # page size

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, height - 40, f"Invoice - Order #{order.order_id}")

    # Customer details
    c.setFont("Helvetica", 12)
    c.drawString(30, height - 80, f"Customer: {order.user.get_full_name()}")
    c.drawString(30, height - 100, f"Email: {order.user.email}")

    # Order details
    c.drawString(30, height - 140, f"Order Date: {order.created_at}")
    c.drawString(30, height - 160, f"Total Amount: INR {order.final_price}")

    # Items table header
    c.drawString(30, height - 200, "Product")
    c.drawString(200, height - 200, "Quantity")
    c.drawString(300, height - 200, "Price")
    c.drawString(400, height - 200, "Total")

    # Loop through the order items
    y_position = height - 220
    for item in order.items.all():
        c.drawString(30, y_position, item.variant.product.name)
        c.drawString(200, y_position, str(item.quantity))
        c.drawString(300, y_position, str(item.variant.price))
        c.drawString(400, y_position, str(item.quantity * item.variant.price))
        y_position -= 20

    # Save the PDF to the buffer
    c.save()

    # Get the value of the BytesIO buffer and return it in the HTTP response
    buffer.seek(0)
    return buffer
