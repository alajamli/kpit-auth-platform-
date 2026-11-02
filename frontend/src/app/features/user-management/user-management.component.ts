import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatSelectModule } from '@angular/material/select';
import { MatCardModule } from '@angular/material/card';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { UserService, User } from '../../core/services/user.service';
import { MatTooltipModule } from '@angular/material/tooltip';

@Component({
  selector: 'app-user-management',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatTableModule,
    MatSelectModule,
    MatCardModule,
    MatInputModule,
    MatFormFieldModule,
    MatButtonModule,
    MatIconModule,
    MatSnackBarModule,
    MatProgressBarModule,
    MatTooltipModule
  ],
  templateUrl: './user-management.component.html',
  styleUrls: ['./user-management.component.scss']
})
export class UserManagementComponent implements OnInit {
  users: User[] = [];
  displayedColumns: string[] = ['name', 'email', 'login', 'role', 'status', 'assign_role', 'actions'];

  isLoading = false;
  showCreateForm = false;
  addUserForm: FormGroup;
  rolesList: string[] = ['admin', 'tester', 'auditor', 'viewer'];

  constructor(
    private userService: UserService,
    private snackBar: MatSnackBar,
    private fb: FormBuilder
  ) {
    this.addUserForm = this.fb.group({
      first_name: ['', Validators.required],
      last_name: ['', Validators.required],
      email: ['', [Validators.required, Validators.email]],
      login: ['', [Validators.required, Validators.minLength(3)]],
      password: ['', [Validators.required, Validators.minLength(6)]],
      role: ['tester', Validators.required]
    });
  }

  ngOnInit(): void {
    this.loadUsers();
  }

  loadUsers(): void {
    this.isLoading = true;
    this.userService.getUsers().subscribe({
      next: (res) => {
        this.isLoading = false;
        if (res.success) {
          this.users = res.users;
        }
      },
      error: (err) => {
        this.isLoading = false;
        this.snackBar.open(err.error?.error || 'Failed to load user directory.', 'Close', { duration: 4000 });
      }
    });
  }

  toggleAddUserForm(): void {
    this.showCreateForm = !this.showCreateForm;
    if (!this.showCreateForm) {
      this.addUserForm.reset({ role: 'tester' });
    }
  }

  onCreateUser(): void {
    if (this.addUserForm.invalid) return;

    this.isLoading = true;
    this.userService.createUser(this.addUserForm.value).subscribe({
      next: () => {
        this.isLoading = false;
        this.snackBar.open('New user created successfully!', 'Close', { duration: 3000 });
        this.showCreateForm = false;
        this.addUserForm.reset({ role: 'tester' });
        this.loadUsers();
      },
      error: (err) => {
        this.isLoading = false;
        this.snackBar.open(err.error?.error || 'Failed to create user.', 'Close', { duration: 4000 });
      }
    });
  }

  onRoleChange(user: User, newRole: string): void {
    if (user.role === newRole) return;

    this.userService.updateUserRole(user.id, newRole).subscribe({
      next: () => {
        user.role = newRole as any;
        this.snackBar.open(`Role updated to ${newRole.toUpperCase()} for ${user.first_name}`, 'Close', { duration: 3000 });
      },
      error: (err) => {
        this.snackBar.open(err.error?.error || 'Failed to update role.', 'Close', { duration: 4000 });
        this.loadUsers();
      }
    });
  }

  onDeleteUser(user: User): void {
    this.userService.deleteUser(user.id).subscribe({
      next: () => {
        this.snackBar.open(`User ${user.login} deleted successfully.`, 'Close', { duration: 3000 });
        this.loadUsers();
      },
      error: (err) => {
        this.snackBar.open(err.error?.error || 'Failed to delete user.', 'Close', { duration: 4000 });
      }
    });
  }

  getRoleBadgeClass(role: string): string {
    switch (role) {
      case 'admin': return 'badge-admin';
      case 'tester': return 'badge-tester';
      case 'auditor': return 'badge-auditor';
      default: return 'badge-viewer';
    }
  }
  onToggleStatus(user: User): void {
  this.userService.toggleUserStatus(user.id).subscribe({
    next: (res) => {
      user.is_verified = res.is_verified;
      const statusText = res.is_verified ? 'enabled' : 'disabled';
      this.snackBar.open(`Account for ${user.login} is now ${statusText}.`, 'Close', { duration: 3000 });
    },
    error: (err) => {
      this.snackBar.open(err.error?.error || 'Failed to update account status.', 'Close', { duration: 4000 });
    }
  });
}
}