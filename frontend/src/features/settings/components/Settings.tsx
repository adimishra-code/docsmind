import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { useAuthStore } from '@/store/useAuthStore';
import { useTheme } from '@/providers/theme-provider';
import { authApi } from '@/services/authApi';
import { toast } from '@/components/ui/use-toast';
import { Sun, Moon, Monitor, Loader2, Check, AlertTriangle } from 'lucide-react';

export function Settings() {
  const user = useAuthStore((state) => state.user);
  const setUser = useAuthStore((state) => state.setUser);
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const { theme, setTheme } = useTheme();

  const [name, setName] = useState(user?.full_name ?? '');
  const [isSaving, setIsSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);

  const handleSaveProfile = async () => {
    setIsSaving(true);
    try {
      const updated = await authApi.updateMe(name.trim() || null);
      setUser(updated);
      setSaved(true);
      toast({ title: 'Profile updated', description: 'Your display name has been saved.' });
      setTimeout(() => setSaved(false), 3000);
    } catch {
      toast({ title: 'Failed to save', variant: 'destructive', description: 'Could not update your profile. Please try again.' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteAccount = async () => {
    setIsDeleting(true);
    try {
      await authApi.deleteMe();
      toast({
        title: 'Account deleted',
        description: 'Your account and all associated data have been permanently removed.',
      });
      setShowDeleteDialog(false);
      clearAuth();
    } catch {
      toast({
        title: 'Deletion failed',
        variant: 'destructive',
        description: 'We could not delete your account. Please try again.',
      });
    } finally {
      setIsDeleting(false);
    }
  };

  const nameChanged = (name.trim() || null) !== (user?.full_name ?? null);

  return (
    <div className="p-6 max-w-[800px] mx-auto space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-1">Manage your account and preferences.</p>
      </div>

      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="appearance">Appearance</TabsTrigger>
          <TabsTrigger value="danger">Danger Zone</TabsTrigger>
        </TabsList>

        <TabsContent value="profile" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Profile</CardTitle>
              <CardDescription>Update your account information.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="settings-name">Full Name</Label>
                <Input
                  id="settings-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Your display name"
                  disabled={isSaving}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="settings-email">Email</Label>
                <Input
                  id="settings-email"
                  value={user?.email ?? ''}
                  disabled
                  className="opacity-60 cursor-not-allowed"
                />
                <p className="text-xs text-muted-foreground">Email cannot be changed.</p>
              </div>
              <div className="flex items-center gap-3 pt-2">
                <Button
                  onClick={handleSaveProfile}
                  disabled={isSaving || !nameChanged}
                  className="gap-2"
                >
                  {isSaving ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : saved ? (
                    <Check className="h-4 w-4" />
                  ) : null}
                  {saved ? 'Saved!' : 'Save Changes'}
                </Button>
                {!nameChanged && !isSaving && (
                  <p className="text-xs text-muted-foreground">No unsaved changes</p>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="appearance" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Appearance</CardTitle>
              <CardDescription>Customize the look and feel of DocsMind.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <Label>Theme</Label>
                <div className="flex gap-2">
                  {[
                    { value: 'light', icon: Sun, label: 'Light' },
                    { value: 'dark', icon: Moon, label: 'Dark' },
                    { value: 'system', icon: Monitor, label: 'System' },
                  ].map((option) => (
                    <Button
                      key={option.value}
                      variant={theme === option.value ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setTheme(option.value as any)}
                      className="gap-2"
                    >
                      <option.icon className="h-4 w-4" />
                      {option.label}
                    </Button>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="danger" className="space-y-6">
          <Card className="border-destructive/50">
            <CardHeader>
              <CardTitle className="text-base text-destructive flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" /> Danger Zone
              </CardTitle>
              <CardDescription>
                These actions are permanent and cannot be undone.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Delete Account</p>
                  <p className="text-sm text-muted-foreground">Permanently delete your account and all data.</p>
                </div>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => setShowDeleteDialog(true)}
                >
                  Delete Account
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Delete Account Confirmation */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              Delete your account?
            </DialogTitle>
            <DialogDescription>
              This will permanently delete your account, all documents, conversations, and data. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2 py-2">
            <Label htmlFor="delete-confirm">
              Type <strong>delete my account</strong> to confirm
            </Label>
            <Input
              id="delete-confirm"
              value={deleteConfirmText}
              onChange={(e) => setDeleteConfirmText(e.target.value)}
              placeholder="delete my account"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)} disabled={isDeleting}>Cancel</Button>
            <Button
              variant="destructive"
              disabled={deleteConfirmText !== 'delete my account' || isDeleting}
              onClick={handleDeleteAccount}
              className="gap-2"
            >
              {isDeleting && <Loader2 className="h-4 w-4 animate-spin" />}
              Delete Account
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
