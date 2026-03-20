from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from tickets.models import DepartmentFAQ

STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "do", "does", "did",
    "how", "what", "when", "where", "who", "why", "which",
    "i", "me", "my", "we", "our", "you", "your",
    "to", "of", "in", "for", "on", "at", "by", "with", "from",
    "and", "or", "but", "not", "no", "so", "if", "can", "will",
    "it", "its", "this", "that", "has", "have", "had",
}

MIN_KEYWORD_LENGTH = 3


@login_required
def search_faqs(request):
    """Search department FAQs by matching keywords from the query."""
    q = request.GET.get("q", "").strip()
    department_ids = request.GET.getlist("departments")

    keywords = extract_keywords(q)
    if not keywords:
        return JsonResponse([], safe=False)

    faqs = find_matching_faqs(keywords, department_ids)
    results = format_faq_results(faqs)

    return JsonResponse(results, safe=False)


def extract_keywords(text):
    """Extract meaningful keywords by removing stop words and short words."""
    words = text.lower().split()
    return [
        word for word in words
        if word not in STOP_WORDS and len(word) >= MIN_KEYWORD_LENGTH
    ]


def find_matching_faqs(keywords, department_ids):
    """Find FAQs matching any of the given keywords, optionally filtered by departments."""
    query = Q()
    for keyword in keywords:
        query |= Q(question__icontains=keyword) | Q(answer__icontains=keyword)

    faqs = DepartmentFAQ.objects.filter(query).select_related("department")

    if department_ids:
        faqs = faqs.filter(department_id__in=department_ids)

    return faqs.distinct()[:5]


def format_faq_results(faqs):
    """Format FAQ results for the JSON response."""
    return [
        {
            "id": faq.id,
            "question": faq.question,
            "answer": faq.answer,
            "department": faq.department.name,
        }
        for faq in faqs
    ]
