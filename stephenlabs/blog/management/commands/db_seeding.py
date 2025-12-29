from django.core.management.base import BaseCommand
from django.utils.text import slugify
from blog.models import Category, Tag


CATEGORIES = [
    {"name": "Computer Science", "description": "Core concepts covering software systems, hardware fundamentals, algorithms, and computational thinking."},
    {"name": "Backend Engineering", "description": "Server-side development, APIs, databases, and backend architecture."},
    {"name": "Web Development", "description": "Modern web technologies, frontend-backend integration, and web architecture."},
    {"name": "Blockchain & Web3", "description": "Decentralized systems, smart contracts, blockchain protocols, and Web3 engineering."},
    {"name": "DevOps & Infrastructure", "description": "Deployment pipelines, cloud infrastructure, automation, and system reliability."},
    {"name": "System Design", "description": "Scalable architectures, design trade-offs, and distributed systems."},
    {"name": "Tutorials & Guides", "description": "Hands-on walkthroughs and practical engineering tutorials."},
    {"name": "Technical Writing", "description": "Developer-focused writing and documentation."},
    {"name": "Research & Insights", "description": "Deep technical analysis and engineering insights."},
    {"name": "Career & Learning", "description": "Engineering growth, learning paths, and career development."},
]

TAGS = [
    "computer-science", "algorithms", "data-structures", "operating-systems",
    "computer-architecture", "networking", "databases",
    "python", "django", "rest-api", "backend", "web-development",
    "authentication", "authorization", "security", "performance",
    "devops", "docker", "kubernetes", "ci-cd", "linux",
    "bash", "cloud", "deployment", "monitoring",
    "blockchain", "web3", "ethereum", "solidity",
    "smart-contracts", "defi", "nft", "layer-2", "cryptography",
    "system-design", "scalability", "distributed-systems",
    "microservices", "architecture",
    "technical-writing", "documentation", "api-docs",
    "learning-in-public", "tutorials", "best-practices",
]


class Command(BaseCommand):
    help = "Seed initial categories and tags for the blog"

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding categories...")

        for item in CATEGORIES:
            Category.objects.get_or_create(
                name=item["name"],
                defaults={
                    "slug": slugify(item["name"]),
                    "description": item["description"],
                }
            )

        self.stdout.write(self.style.SUCCESS("Categories seeded successfully."))

        self.stdout.write("Seeding tags...")

        for tag in TAGS:
            Tag.objects.get_or_create(
                name=tag.replace("-", " ").title(),
                defaults={"slug": tag}
            )

        self.stdout.write(self.style.SUCCESS("Tags seeded successfully."))
