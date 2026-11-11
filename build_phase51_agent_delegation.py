#!/usr/bin/env python3
"""NyumbaLink Phase 51: Agent Delegation & Property Authority."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()

# ----------------------------------------------------------------
# 1. Update Views & Serializers
# ----------------------------------------------------------------
SERIALIZERS_FILE = ROOT / "apps" / "properties" / "serializers.py"
text = SERIALIZERS_FILE.read_text(encoding="utf-8")

if "class PropertyAuthoritySerializer" not in text:
    text += '''

class PropertyAuthoritySerializer(serializers.ModelSerializer):
    granted_to_email = serializers.CharField(source="granted_to.email", read_only=True)
    
    class Meta:
        from .models import PropertyAuthority
        model = PropertyAuthority
        fields = ("id", "property", "granted_to", "granted_to_email", "granted_by", "can_list", "can_edit", "expires_at", "revoked_at")
        read_only_fields = ("id", "granted_by", "revoked_at")
'''
    SERIALIZERS_FILE.write_text(text, encoding="utf-8")
    print("✅ Added PropertyAuthoritySerializer")

VIEWS_FILE = ROOT / "apps" / "properties" / "views.py"
text = VIEWS_FILE.read_text(encoding="utf-8")

if "class PropertyAuthorityViewSet" not in text:
    text = text.replace(
        "from .serializers import (",
        "from .serializers import (\n    PropertyAuthoritySerializer,"
    )
    
    text += '''

class PropertyAuthorityViewSet(viewsets.ModelViewSet):
    serializer_class = PropertyAuthoritySerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        # Landlords see who they granted access to; Agents see what they have access to
        from django.db.models import Q
        return PropertyAuthority.objects.filter(
            Q(granted_by=self.request.user) | Q(granted_to=self.request.user)
        ).select_related("property", "granted_to")

    def perform_create(self, serializer):
        property_id = self.request.data.get("property")
        email = self.request.data.get("granted_to_email")
        
        from django.contrib.auth import get_user_model
        from .models import Property
        from apps.notifications.services import create_notification
        
        User = get_user_model()
        prop = Property.objects.get(id=property_id)
        
        if prop.submitted_by != self.request.user:
            raise permissions.PermissionDenied("Only the property owner can grant authority.")
            
        agent = User.objects.filter(email__iexact=email).first()
        if not agent:
            raise serializers.ValidationError("No user found with that email.")
            
        authority = serializer.save(property=prop, granted_to=agent, granted_by=self.request.user)
        
        create_notification(
            user=agent,
            title="New Property Access",
            message=f"You have been granted access to manage {prop.neighbourhood.name}.",
            link=f"/dashboard"
        )
'''
    VIEWS_FILE.write_text(text, encoding="utf-8")
    print("✅ Added PropertyAuthorityViewSet")

URLS_FILE = ROOT / "apps" / "properties" / "urls.py"
text = URLS_FILE.read_text(encoding="utf-8")
if 'router.register("authorities"' not in text:
    text = text.replace(
        'router.register("hero-images", HeroImageViewSet, basename="hero-image")',
        'router.register("hero-images", HeroImageViewSet, basename="hero-image")\nrouter.register("authorities", PropertyAuthorityViewSet, basename="authority")'
    )
    URLS_FILE.write_text(text, encoding="utf-8")
    print("✅ Mounted PropertyAuthorityViewSet")

print("\n🚀 Pushing backend changes to GitHub...")
subprocess.run(["git", "add", "."], cwd=ROOT)
subprocess.run(["git", "commit", "-m", "Feat: Add Property Authority endpoints for agent delegation"], cwd=ROOT)
subprocess.run(["git", "push", "origin", "main"], cwd=ROOT)