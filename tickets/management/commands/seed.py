import random
from faker import Faker
from random import randint, choice, sample
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from tickets.models import *
from django.contrib.contenttypes.models import ContentType
from tickets.models.notification import Notification
from collections import defaultdict

user_fixtures = [
    {'username': 'johndoe', 'email': 'johndoe@example.org', 'first_name': 'John', 'last_name': 'Doe', 'superuser' : True, 'staff': True},
    {'username': 'janedoe', 'email': 'janedoe@example.org', 'first_name': 'Jane', 'last_name': 'Doe', 'staff': True},
    {'username': 'janetdoe', 'email': 'janetdoe@example.org', 'first_name': 'Janet', 'last_name': 'Doe', 'staff': True},
    {'username': 'charlie', 'email': 'charliejohnson@example.org', 'first_name': 'Charlie', 'last_name': 'Johnson'},
    {'username': 'bo', 'email': 'bo@example.org', 'first_name': 'Bo', 'last_name': 'Smith'},
]

department_fixtures = [
    {'name': 'Informatics', 'description': 'Handles all issues related to Informatics', 'created_by': 'janedoe'},
]

generic_department_faq_templates = [
    {
        "question": "How do I contact {department} about my query?",
        "answer": (
            "Raise a ticket with your full name, K number, programme details, and a short summary "
            "of the issue so the {department} team can route it quickly."
        ),
    },
    {
        "question": "What details should I include when I submit a query to {department}?",
        "answer": (
            "Include your university email address, student ID, the relevant module or service, any deadlines, "
            "and screenshots or documents that help explain the request."
        ),
    },
]

department_specific_faqs = {
    "Informatics": [
        {
            "question": "How do I report a KEATS, lab machine, or coding environment issue in Informatics?",
            "answer": (
                "Share the module name, device or lab location, exact error message, and when the issue started. "
                "If it is coursework-related, mention any deadline so Informatics staff can prioritise the request."
            ),
        },
    ],
    "IT Service Desk": [
        {
            "question": "How do I reset my password for KEATS, email, or Student Records?",
            "answer": (
                "Use the King's password reset service first. If the reset does not work, raise a ticket with "
                "your K number, the affected service, and a screenshot of the error."
            ),
        },
        {
            "question": "How do I connect my laptop or phone to eduroam?",
            "answer": (
                "Use your full university email address as the username and your current password. If setup fails, "
                "tell the IT Service Desk your device type, campus, and the step where the connection breaks."
            ),
        },
    ],
    "Registry Services": [
        {
            "question": "How do I update my legal name or personal details on my student record?",
            "answer": (
                "Contact Registry Services with your student ID and supporting evidence, such as official ID or a "
                "document showing the change. The team will confirm what can be updated in Student Records."
            ),
        },
    ],
    "Student Records": [
        {
            "question": "How do I request an official transcript or council tax letter from Student Records?",
            "answer": (
                "Submit the request through the student documents process and include your student ID, delivery "
                "preference, and any deadline for the letter or transcript."
            ),
        },
    ],
    "Timetabling Office": [
        {
            "question": "Who do I contact if my timetable is missing a lecture, seminar, or lab?",
            "answer": (
                "Send the module code, teaching week, and the activity that is missing from your timetable. "
                "The Timetabling Office can then check whether the session has moved or not yet been published."
            ),
        },
    ],
    "Assessment and Examinations": [
        {
            "question": "How do I check my exam timetable or report an exam clash?",
            "answer": (
                "Include your student ID, module codes, and the exams that appear to clash. The Assessment and "
                "Examinations team can confirm the timetable and explain the next steps."
            ),
        },
    ],
    "Library Services": [
        {
            "question": "How do I access an online journal, e-book, or reading list item through the library?",
            "answer": (
                "Share the resource title, module, and the link you tried. Library Services can check access rights, "
                "database availability, and whether a reading list link needs updating."
            ),
        },
    ],
    "Student Funding": [
        {
            "question": "How do I ask about tuition fee instalments, bursaries, or hardship funding?",
            "answer": (
                "Include your K number, programme, funding concern, and any urgent deadline. Student Funding can "
                "advise on payment dates, evidence requirements, and available support."
            ),
        },
    ],
    "Wellbeing and Counselling": [
        {
            "question": "How do I access wellbeing or counselling support as a student?",
            "answer": (
                "Raise a confidential query with your availability and a brief outline of the support you need. "
                "If you need urgent help, follow the emergency guidance rather than waiting for a routine reply."
            ),
        },
    ],
    "Disability Support and Inclusion": [
        {
            "question": "How do I register with Disability Support and Inclusion for adjustments?",
            "answer": (
                "Share your student ID, programme, and any supporting medical evidence you already have. The team "
                "will explain the registration process and the timeline for putting adjustments in place."
            ),
        },
    ],
    "King's Language Centre": [
        {
            "question": "How do I enrol on a King's Language Centre module or evening language course?",
            "answer": (
                "Include the language, level, and whether you need the class for credit or personal study. The "
                "Language Centre can confirm availability, eligibility, and enrolment steps."
            ),
        },
    ],
    "Careers and Employability": [
        {
            "question": "How do I book a CV check or careers appointment through King's Careers and Employability?",
            "answer": (
                "Send your preferred appointment type, your course or career goal, and any deadline such as an "
                "application closing date so the team can point you to the right service."
            ),
        },
    ],
    "Accommodation Services": [
        {
            "question": "How do I report a maintenance issue or room concern in student accommodation?",
            "answer": (
                "Include your residence, room number, photos if relevant, and whether the issue affects safety. "
                "Accommodation Services can then route it to the correct residence or maintenance team."
            ),
        },
    ],
    "Visa and International Advice": [
        {
            "question": "How do I ask for visa or CAS advice before travelling or re-enrolling?",
            "answer": (
                "Explain your visa type, travel dates, and the question you need answered. Include your student ID "
                "so the Visa and International Advice team can give the right guidance."
            ),
        },
    ],
    "Graduation Office": [
        {
            "question": "How do I check my graduation eligibility or ceremony booking?",
            "answer": (
                "Include your student ID, programme, and expected completion date. The Graduation Office can confirm "
                "whether you are eligible and what actions are still outstanding."
            ),
        },
    ],
    "Student Conduct and Appeals": [
        {
            "question": "How do I submit an academic appeal or ask about the student conduct process?",
            "answer": (
                "Share the decision you are querying, the date you received it, and any evidence you already have. "
                "The team can explain the correct route and the deadline that applies to your case."
            ),
        },
    ],
    "Digital Education": [
        {
            "question": "Who should I contact if a KEATS submission, quiz, or Turnitin link is not working?",
            "answer": (
                "Send the module code, the KEATS activity link, the deadline, and a screenshot of the issue. "
                "Digital Education can help determine whether it is a setup problem or a wider platform issue."
            ),
        },
    ],
    "King's Online Support": [
        {
            "question": "How do I get help with accessing online teaching or recorded classes?",
            "answer": (
                "Let King's Online Support know the module, platform, device, and what happens when you try to join "
                "or replay the session so they can troubleshoot efficiently."
            ),
        },
    ],
    "Module Registration Team": [
        {
            "question": "How do I change modules or check my module registration?",
            "answer": (
                "Include your programme, current modules, and the module you want to add or drop. The Module "
                "Registration Team can confirm deadlines, availability, and any approval needed."
            ),
        },
    ],
    "Academic Skills Centre": [
        {
            "question": "How do I book academic writing, study skills, or revision support?",
            "answer": (
                "Share the kind of support you want, your course, and any upcoming assessment deadline. The "
                "Academic Skills Centre can direct you to workshops, tutorials, or self-study resources."
            ),
        },
    ],
}

kcl_department_pool = [
    "IT Service Desk",
    "Registry Services",
    "Student Records",
    "Timetabling Office",
    "Assessment and Examinations",
    "Library Services",
    "Student Funding",
    "Wellbeing and Counselling",
    "Disability Support and Inclusion",
    "King's Language Centre",
    "Careers and Employability",
    "Accommodation Services",
    "Visa and International Advice",
    "Campus Operations",
    "Estates and Facilities",
    "King's Business School Administration",
    "Faculty of Arts and Humanities Office",
    "Faculty of Natural, Mathematical & Engineering Sciences Office",
    "Faculty of Life Sciences and Medicine Office",
    "Dickson Poon School of Law Administration",
    "Nursing and Midwifery Student Office",
    "Research Student Support",
    "Graduation Office",
    "Student Conduct and Appeals",
    "Digital Education",
    "King's Online Support",
    "Global Mobility Team",
    "Personal Tutoring Support",
    "Module Registration Team",
    "Academic Skills Centre",
]

faq_tickets = [
    {'title': 'How do I access my course materials and lecture recordings?', 'body': 'I\'m trying to find the recorded lectures from last week\'s lectures. Could you help me understand where to access them on the university portal?'},
    {'title': 'How can I request an extension on my assignment?', 'body': 'I have a deadline approaching and I need to request an extension due to unexpected circumstances. What\'s the process and who should I contact?'},
    {'title': 'What is the deadline for module registration?', 'body': 'I need to know the final date for switching modules. Can you provide the academic calendar deadline?'},
    {'title': 'How do I get support from the academic writing centre?', 'body': 'I would like to improve my academic writing skills. Are there drop-in sessions available or do I need to book an appointment?'},
    {'title': 'Can I attend lectures online if I\'m unwell?', 'body': 'I\'m currently recovering from illness and would like to know if the lectures I\'m missing are available to watch online.'},
    
    {'title': 'I cannot log into the university portal', 'body': 'I\'m getting an error message when trying to access my student portal. I\'ve tried resetting my password but it\'s not working.'},
    {'title': 'How do I set up my university email on my personal device?', 'body': 'I want to check my university email on my phone. Could you guide me through the setup process?'},
    {'title': 'The library WiFi keeps disconnecting', 'body': 'Every time I try to study in the library, my WiFi connection drops. This is making it difficult to work. Can this be fixed?'},
    {'title': 'How do I access remote desktop services?', 'body': 'I need to access the university computers from home. What software do I need and how do I connect?'},
    {'title': 'What is the file storage limit for my university cloud account?', 'body': 'I\'m running out of space on my university cloud storage. What are the limits and can they be increased?'},
    
    {'title': 'How do I apply for student accommodation?', 'body': 'I\'m a first-year student and would like to live on campus. When does the accommodation application period open and what are the requirements?'},
    {'title': 'What facilities are available at each campus?', 'body': 'I want to know what study spaces, sports facilities, and cafes are available at the different university campuses.'},
    {'title': 'Is there maintenance being done on my halls of residence?', 'body': 'There\'s been a lot of noise and activity outside my accommodation. Can someone explain what work is being done and when it will be completed?'},
    {'title': 'How do I report a maintenance issue in my student accommodation?', 'body': 'The heating in my room isn\'t working properly and it\'s getting very cold. How do I request a maintenance repair?'},
    {'title': 'Are there quiet study areas available on campus?', 'body': 'I\'m looking for peaceful places to study without distractions. Where can I find quiet study zones?'},
    
    {'title': 'When is the tuition fee payment deadline?', 'body': 'I need to know the deadline for the next installment of my tuition fees. Are there any penalties for late payment?'},
    {'title': 'How do I apply for a student bursary or financial aid?', 'body': 'I\'m facing financial difficulties and would like to know what support is available. What\'s the application process?'},
    {'title': 'Can I get a receipt for my course fees?', 'body': 'I need an official receipt showing that I\'ve paid my fees for tax purposes. How do I obtain this?'},
    {'title': 'What does my student loan cover?', 'body': 'I\'m unclear about what expenses are covered by my student loan and what I need to pay for separately.'},
    
    {'title': 'How do I access mental health support services?', 'body': 'I\'m feeling overwhelmed with my studies and personal circumstances. What counselling or mental health services are available to students?'},
    {'title': 'What support is available for students with disabilities?', 'body': 'I have a disability and would like to know what accommodations and support services the university offers.'},
    {'title': 'How do I get support if I\'m experiencing harassment or discrimination?', 'body': 'I\'ve experienced an incident on campus and I\'m not sure how to report it or what support is available.'},
    {'title': 'Are there peer support and mentoring programs?', 'body': 'Would like to get involved in peer support or find a mentor to help me with my student journey.'},
    {'title': 'What health services are available to students?', 'body': 'I need access to medical services. Is there a student health centre on campus and how do I register?'},
    
    {'title': 'How do I access the careers service?', 'body': 'I\'m in my final year and looking for guidance on job applications and internships. What support does the careers service offer?'},
    {'title': 'Are there internship opportunities available?', 'body': 'I want to gain some work experience. How do I find internship placements through the university?'},
    {'title': 'Can I get my CV reviewed?', 'body': 'I\'ve been applying for jobs but haven\'t had much success. Is there someone who can review my CV and provide feedback?'},
    {'title': 'What professional development workshops are offered?', 'body': 'I\'m interested in developing professional skills. What workshops and training programs does the university offer?'},
    
    {'title': 'How do I defer my studies to next year?', 'body': 'I need to postpone my studies for a year due to personal circumstances. What\'s the process for deferring my enrollment?'},
    {'title': 'Can I change my course after enrollment?', 'body': 'I\'ve realised this course isn\'t the right fit for me. Is it possible to switch to a different program?'},
    {'title': 'What is the attendance requirement?', 'body': 'I\'ve missed several lectures due to illness. Are there minimum attendance requirements I need to meet?'},
    {'title': 'How do I graduate and what is the process?', 'body': 'I\'ve completed my course. What steps do I need to take to formally graduate and receive my degree?'},
    
    {'title': 'How do I renew my library books online?', 'body': 'I\'ve got some books that are due back soon. Can I renew them through the library website?'},
    {'title': 'What databases and journal access do I have?', 'body': 'I need access to academic journals for my research. What databases are available to students?'},
    {'title': 'How long is the library open during exam season?', 'body': 'I\'m preparing for exams and want to study in the library. What are the extended hours during exam period?'},
    {'title': 'Can I request a book that isn\'t currently available?', 'body': 'I need a specific book for my research but it\'s currently on loan. Can I place a reservation?'},
    
    {'title': 'How do I join a student society or club?', 'body': 'I\'m interested in joining clubs on campus. Where can I find information about different societies and how to join?'},
    {'title': 'What events are happening on campus this semester?', 'body': 'I want to get more involved in campus life. What social, cultural, and academic events are coming up?'},
    {'title': 'How do I volunteer at the university?', 'body': 'I\'d like to do some volunteering work. What opportunities are available and how do I get started?'},
    
    {'title': 'What is the university\'s attendance and punctuality policy?', 'body': 'I\'m unclear about expectations regarding attendance at lectures and practical sessions. Is attendance compulsory?'},
    {'title': 'What happens if I breach the student code of conduct?', 'body': 'I\'ve received a warning about my conduct on campus. What are the potential consequences and what\'s my right to appeal?'},
    {'title': 'How do I appeal an academic decision?', 'body': 'I\'ve received a grade I believe is unfair. What is the appeals process and within what timeframe can I submit an appeal?'},
]

faq_responses = [
    "Thank you for your inquiry. You can find detailed information about this in the student handbook section available on the university portal.",
    "I\'ve checked with the relevant department and here\'s what I found: You should contact the Student Services office located in the main building, ground floor.",
    "Great question! This is something we get asked frequently. The process is quite straightforward - please follow these steps: First, log into your portal; Second, navigate to the relevant section; Third, submit your request.",
    "We completely understand your concern. Most students have similar questions when they start. The answer is available in our FAQ section of the website, but I\'ll summarize: Generally this takes 5-7 working days.",
    "Thank you for reaching out. You\'re not alone with this issue. If you head to the help desk in person or call the support line, they can assist you within 24 hours.",
    "Perfect timing with your question. We just updated our policies on this. Here\'s the new procedure: Please ensure you submit all required documentation before the deadline.",
    "I\'ve escalated your request to the appropriate team. You should expect a response within 48 hours. In the meantime, please keep any relevant documentation handy.",
    "Thanks for bringing this to our attention. This is actually a common concern amongst students. The best solution is to speak with your personal tutor or module leader.",
    "Great question - this is something many students need clarification on. The university provides 24/7 support through multiple channels: email, phone, and in-person.",
    "I understand this might be frustrating. Let\'s get this resolved for you. I\'ve submitted a support ticket to our technical team who typically respond within one business day.",
]

faq_bodies_by_title = {ticket['title']: ticket['body'] for ticket in faq_tickets}

fallback_ticket_bodies = [
    "I am writing to request advice on this issue. I have reviewed the guidance online but I am still unsure of the correct process.",
    "Please could you advise on the next step for this query? I would appreciate clarification at your earliest convenience.",
    "I would be grateful if your team could confirm who should handle this request and what information you need from me.",
    "I have attached the relevant details and would appreciate support in resolving this matter.",
]

follow_up_responses = [
    "Thank you for the response, this was very helpful!",
    "I appreciate the help. This has clarified things for me.",
    "Thanks for the quick response. I'll proceed with that approach.",
    "Perfect, I'll follow those steps and let you know if I need further assistance.",
    "This is exactly what I needed. Thank you!",
    "Great, I understand now. Much appreciated!",
]

realistic_filenames = [
    "Course_Schedule.pdf",
    "Assignment_Guidelines.docx",
    "Student_Handbook.pdf",
    "Support_Resources.txt",
    "Accommodation_Info.pdf",
    "IT_Setup_Guide.docx",
    "Financial_Aid_Application.pdf",
    "Course_Notes.pdf",
    "Lab_Report_Template.docx",
    "Exam_Timetable.pdf",
    "Module_Syllabus.pdf",
    "Research_References.docx",
    "Appeal_Form.pdf",
    "Evidence_Document.pdf",
    "Transcript.pdf",
    "Recommendation_Letter.docx",
    "Supporting_Evidence.pdf",
]

class Command(BaseCommand):
    """Build automation command to seed the database with data."""
    USER_COUNT = 100
    DEPARTMENT_COUNT = 30
    TICKET_COUNT = 200
    DEFAULT_PASSWORD = 'Password123'

    def __init__(self, *args, **kwargs):
        """Initialize the command with a locale-specific Faker instance."""
        super().__init__(*args, **kwargs)
        self.faker = Faker('en_GB')
        self.faker.seed_instance(1234)
        random.seed(1234)

    def handle(self, *args, **options):
        """
        Runs the full seeding workflow and stores the data for any
        post-processing or debugging (not required for operation).
        """
        self.create_users()
        self.create_departments()
        self.assign_users_to_departments()
        self.create_department_faqs()
        self.create_tickets()
        self.assign_tickets_to_departments()
        self.create_ticket_messages()
        self.create_ticket_attachments()
        self.assign_staff_to_tickets()
        self.create_department_invitations()
        self.create_notifications()
    
    def create_users(self):
        """Create users in the database."""
        print("Creating users...")
        self.create_known_users()
        self.create_random_staff_users()
        self.create_random_users()
        print(f"{User.objects.count()} Users created.")

    def create_known_users(self):
        """Create users from predefined fixtures."""
        for fixture in user_fixtures: 
            User.objects.create_user(
                username=fixture['username'], email=fixture['email'], password=self.DEFAULT_PASSWORD,
                first_name=fixture['first_name'], last_name=fixture['last_name'],
                is_superuser=fixture.get('superuser', False), is_staff=fixture.get('staff', False)
            )

    def create_random_staff_users(self):
        """Create random staff users using Faker library."""
        for _ in range((self.USER_COUNT - len(user_fixtures)) // 2):
            first_name = self.faker.first_name()
            last_name = self.faker.last_name()
            username = f"{first_name.lower()}{last_name.lower()}{randint(1, 9999)}"
            email = f"{username}@example.org"

            self.try_create_user(
                username=username, email=email, password=self.DEFAULT_PASSWORD, 
                first_name=first_name, last_name=last_name, is_staff=True,
            )

    def create_random_users(self):
        """Create random users using Faker library."""
        for _ in range((self.USER_COUNT - len(user_fixtures)) // 2):
            first_name = self.faker.first_name()
            last_name = self.faker.last_name()
            username = f"@{first_name.lower()}{last_name.lower()}{randint(1, 9999)}"
            email = f"{username}@example.org"

            self.try_create_user(
                username=username, email=email, password=self.DEFAULT_PASSWORD,
                first_name=first_name, last_name=last_name,
            )

    def try_create_user(self, **kwargs):
        """Attempt to create a user, handling any errors."""
        try:
            User.objects.create_user(**kwargs)
        except Exception:
            pass

    def create_departments(self):
        """Create departments in the database."""
        print("Creating departments...")
        self.create_known_departments()
        self.create_random_departments()
        print(f"{Department.objects.count()} Departments created.")

    def create_known_departments(self):
        """Create departments from predefined fixtures."""
        for fixture in department_fixtures:
            creator = User.objects.get(username=fixture['created_by'])
            Department.objects.create(
                name=fixture['name'],
                description=fixture.get('description', ''),
                created_by=creator
            )

    def create_random_departments(self):
        """Create university-style department names and descriptions."""
        staff = list(User.objects.filter(is_staff=True))
        existing_names = {dept.name for dept in Department.objects.all()}
        available_names = [name for name in kcl_department_pool if name not in existing_names]
        for index in range(self.DEPARTMENT_COUNT - len(department_fixtures)):
            name = self._department_name_for_index(index, available_names)
            description = (
                "Provides support for students and staff with administrative and academic service requests."
            )
            created_by = choice(staff)

            Department.objects.create(name=name, description=description, created_by=created_by)

    def _department_name_for_index(self, index, available_names):
        """Return the most suitable seeded department name for an index."""
        if index < len(available_names):
            return available_names[index]
        return f"Student Services Unit {index + 1}"

    def try_create_department(self, **kwargs):
        """Attempt to create a department, handling any errors."""
        try:
            Department.objects.create(**kwargs)
        except Exception:
            pass

    def create_department_faqs(self):
        """Create university-style FAQs for every seeded department."""
        print("Creating department FAQs...")
        created = 0

        for department in Department.objects.all().order_by("name"):
            faq_entries = self._faq_entries_for_department(department)
            for order, faq in enumerate(faq_entries):
                _, was_created = DepartmentFAQ.objects.get_or_create(
                    department=department,
                    question=faq["question"],
                    defaults={
                        "answer": faq["answer"],
                        "created_by": department.created_by,
                        "order": order,
                    },
                )
                if was_created:
                    created += 1

        print(f"{created} Department FAQs created.")

    def _faq_entries_for_department(self, department):
        """Return generic and department-specific FAQ entries for a department."""
        formatted_generic_entries = [
            {
                "question": template["question"].format(department=department.name),
                "answer": template["answer"].format(department=department.name),
            }
            for template in generic_department_faq_templates
        ]
        return formatted_generic_entries + department_specific_faqs.get(department.name, [])

    def assign_users_to_departments(self):
        """Randomly assign users to departments."""
        print("Assigning users to departments...")
        users = list(User.objects.filter(is_staff=True))
        departments = list(Department.objects.all())
        
        for department in departments:
            UserDepartments.objects.get_or_create(user=department.created_by, department=department)
            num_assignments = randint(5, 10)
            assigned_users = random.sample(users, num_assignments)
            self.add_users_to_department(assigned_users, department)

        print("User assignments complete.")

    def add_users_to_department(self, users, department):
        """Assign multiple users to a department."""
        for user in users:
            UserDepartments.objects.get_or_create(user=user, department=department)

    def create_tickets(self):
        """Create tickets in the database using FAQ-style content."""
        print("Creating tickets...")
        users = list(User.objects.all())
        self._create_seeded_faq_tickets(users)
        self._create_remaining_tickets(users)
        print(f"{Ticket.objects.count()} Tickets created.")

    def _create_seeded_faq_tickets(self, users):
        """Create one ticket per FAQ entry."""
        for faq in faq_tickets:
            self._create_ticket_with_title(faq['title'], users)

    def _create_remaining_tickets(self, users):
        """Fill up ticket count using FAQ-style titles."""
        remaining = self.TICKET_COUNT - len(faq_tickets)
        for _ in range(max(0, remaining)):
            self._create_ticket_with_title(choice(faq_tickets)['title'], users)

    def _create_ticket_with_title(self, title, users):
        """Create a single ticket with a realistic title."""
        Ticket.objects.create(
            title=title,
            status=choice(['open', 'closed']),
            created_by=choice(users),
        )

    def assign_tickets_to_departments(self):
        """Randomly assign tickets to departments."""
        print("Assigning tickets to departments...")

        tickets = list(Ticket.objects.all())
        departments = list(Department.objects.all())

        for ticket in tickets:
            num_assignments = randint(1, 3)
            available_departments = random.sample(departments, num_assignments)
            self.add_tickets_to_department(ticket, available_departments)

        print("Ticket assignments complete.")

    def add_tickets_to_department(self, ticket, departments):
        """Assign multiple tickets to multiple departments."""
        for department in departments:
            TicketAssigned.objects.get_or_create(ticket=ticket, department=department)

    def create_ticket_messages(self):
        """Create ticket messages in the database using FAQ-style responses."""
        print("Creating ticket messages...")
        tickets = list(Ticket.objects.all())
        
        for ticket in tickets:
            initial_body = faq_bodies_by_title.get(ticket.title, choice(fallback_ticket_bodies))
            TicketMessage.objects.get_or_create(
                ticket=ticket,
                body=initial_body,
                sender=ticket.created_by,
            )
            self.create_ticket_response_messages(ticket)

        print("Ticket messages created.")
    
    def create_ticket_response_messages(self, ticket):
        """Create response messages from staff using FAQ-style responses."""
        num_messages = randint(2, 4)
        for _ in range(num_messages):
            available_senders = list(User.objects.filter(
                is_staff=True, 
                user__department__assigned_tickets__ticket=ticket
            ).distinct())

            self.create_staff_ticket_response_messages(ticket, available_senders)
            self.random_create_user_ticket_response_messages(ticket)

    def create_staff_ticket_response_messages(self, ticket, available_senders):
        """Create response messages from staff for a ticket using FAQ responses."""
        if available_senders:
            sender = choice(available_senders)
            body = choice(faq_responses)
            TicketMessage.objects.create(ticket=ticket, sender=sender, body=body)
    
    def random_create_user_ticket_response_messages(self, ticket):
        """Randomly create follow-up messages from users for a ticket."""
        if randint(0, 1):
            sender = ticket.created_by
            body = choice(follow_up_responses)
            TicketMessage.objects.create(ticket=ticket, sender=sender, body=body)

    def _create_single_attachment(self, message):
        """Create one attachment for a message with realistic document names."""
        filename = choice(realistic_filenames)
        content = self._attachment_content(filename)
        file_content = ContentFile(content.encode(), name=filename)
        TicketMessageAttachment.objects.create(
            ticket=message.ticket,
            message=message,
            file=file_content,
            original_name=filename,
            content_type=self._attachment_content_type(filename),
            size_bytes=len(content.encode()),
            uploaded_by=message.sender or message.ticket.created_by,
        )

    def _attachment_content(self, filename):
        """Create deterministic readable content for an attached file."""
        return (
            f"{filename}\n\n"
            "This supporting document was uploaded with the ticket to provide relevant evidence "
            "for review by the assigned department."
        )

    def _attachment_content_type(self, filename):
        """Return a basic content type based on file extension."""
        if filename.endswith('.pdf'):
            return "application/pdf"
        return "text/plain"

    def _create_message_attachments(self, message):
        """Create random attachments for a single message."""
        if randint(0, 100) >= 30:
            return 0
        count = randint(1, 3)
        for _ in range(count):
            self._create_single_attachment(message)
        return count

    def create_ticket_attachments(self):
        """Create random attachments for ticket messages."""
        print("Creating ticket attachments...")
        total = sum(self._create_message_attachments(m) for m in TicketMessage.objects.all())
        print(f"{total} Attachments created.")

    def assign_staff_to_tickets(self):
        """Randomly assign staff members as participants to tickets."""
        print("Assigning staff to tickets...")
        tickets = list(Ticket.objects.all())
        staff_users = list(User.objects.filter(is_staff=True))

        for ticket in tickets:
            num_participants = randint(1, 3)
            participants = random.sample(staff_users, num_participants)
            self.add_participants_to_ticket(ticket, participants)

        print("Staff assignments to tickets complete.")

    def add_participants_to_ticket(self, ticket, participants):
        """Assign multiple staff members as participants to a ticket."""
        for user in participants:
            TicketParticipant.objects.get_or_create(ticket=ticket, user=user)

    def _create_invites_for_staff(self, staff, departments):
        """Create 1-3 pending department invites for one staff user."""
        staff_dept_ids = set(
            UserDepartments.objects.filter(user=staff).values_list('department_id', flat=True)
        )
        available = [d for d in departments if d.id not in staff_dept_ids]
        num_invitations = min(randint(1, 3), len(available))
        if num_invitations == 0:
            return
        for department in random.sample(available, num_invitations):
            DepartmentInvitation.objects.get_or_create(
                department=department,
                recipient=staff,
                status='pending',
                defaults={'sender': department.created_by},
            )

    def create_department_invitations(self):
        """Creates a random amount of department invitations between 1 and 3 for staff users."""
        print("Creating department invitations...")
        staff_users = list(User.objects.filter(is_staff=True))
        departments = list(Department.objects.all())
        for staff in staff_users:
            self._create_invites_for_staff(staff, departments)
        print("Department invitations created.")

    def create_notifications(self):
        """Create many realistic notifications for tickets."""
        users, tickets = list(User.objects.all()), list(Ticket.objects.all())
        ct = ContentType.objects.get_for_model(Ticket)
        stats = defaultdict(int)

        total = self._process_initial_tickets(users, tickets, ct, stats)
        total += self._ensure_min_notifs(users, tickets, ct, stats)

        print(f"{total} Notifications created.")

    def _process_initial_tickets(self, users, tickets, ct, stats):
        """Processes the initial wave of ticket notifications."""
        created = 0
        for ticket in tickets:
            created += self._create_multiple_notifs(ticket, users, ct, stats)
        return created

    def _create_multiple_notifs(self, ticket, users, ct, stats):
        """Generates 2 to 6 notifications per ticket."""
        if len(users) < 2: return 0
        
        count = randint(2, 6)
        for _ in range(count):
            actor, recipient = sample(users, 2)
            self._save_notif(actor, recipient, ticket, ct, choice([True, False]))
            stats[actor.id] += 1
        return count

    def _ensure_min_notifs(self, users, tickets, ct, stats):
        """Ensures every user is an actor at least 5 times."""
        created = 0
        for actor in users:
            created += self._fill_quota(actor, users, tickets, ct, stats)
        return created

    def _fill_quota(self, actor, users, tickets, ct, stats):
        """Creates missing notifications for a specific actor."""
        required = max(0, 5 - stats[actor.id])
        for _ in range(required):
            recipient = self._get_random_other(actor, users)
            self._save_notif(actor, recipient, choice(tickets), ct, False)
        return required

    def _get_random_other(self, actor, users):
        """Gets a random user that is not the specified actor."""
        others = [u for u in users if u != actor]
        return choice(others) if others else actor

    def _save_notif(self, actor, recipient, ticket, ct, is_read):
        """Saves a Notification instance to the database."""
        msg = (
            f"{actor.get_full_name() or actor.username} performed an action "
            f"related to the ticket \"{ticket.title}\".\n\n"
            f"You are receiving this notification because you are involved "
            f"in the ticket or were recently added to it."
        )
        Notification.objects.create(
            user=recipient, actor=actor, content_type=ct, object_id=ticket.id,
            notification_type=Notification.NotificationType.TICKET_CREATED,
            short_message=f"{actor.username} interacted with ticket: {ticket.title}",
            is_read=is_read
        )
