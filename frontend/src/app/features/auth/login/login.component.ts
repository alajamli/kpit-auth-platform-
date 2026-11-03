import { Component, OnInit, AfterViewInit, OnDestroy, NgZone } from "@angular/core";
import { CommonModule } from "@angular/common";
import {
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from "@angular/forms";
import { Router } from "@angular/router";

import { MatCardModule } from "@angular/material/card";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatButtonModule } from "@angular/material/button";
import { MatIconModule } from "@angular/material/icon";
import { MatProgressBarModule } from "@angular/material/progress-bar";
import { MatSnackBar, MatSnackBarModule } from "@angular/material/snack-bar";
import {  RouterLink } from '@angular/router'; // <-- 1. Importer RouterLink

import { AuthService } from "../../../core/services/auth.service";
import { ThemeService } from "../../../core/services/theme.service";
import { BrandLogoComponent } from "../../../core/layouts/brand-logo/brand-logo.component";

declare var google: any;

@Component({
  selector: "app-login",
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatSnackBarModule,
    BrandLogoComponent,
    RouterLink
  ],
  templateUrl: "./login.component.html",
  styleUrl: "./login.component.scss",
})
export class LoginComponent implements OnInit, AfterViewInit, OnDestroy {
  loginForm!: FormGroup;
  otpForm!: FormGroup;

  step: "credentials" | "2fa" = "credentials";
  isLoading = false;
  hidePassword = true;
  errorMessage = "";

  // Données de sécurité 2FA
  pendingLogin = "";
  maskedEmail = "";
  anomalyScore = 0;

  // Compte à rebours 2FA
  countdown = 60;
  timerInterval: ReturnType<typeof setInterval> | null = null;
  canResend = false;

  // Client ID Google OAuth2
  private readonly googleClientId = '873850665777-jdo318981smul654qj10q6oc6ehibde3.apps.googleusercontent.com';

  constructor(
    private fb: FormBuilder,
    private authService: AuthService,
    private router: Router,
    private snackBar: MatSnackBar,
    private ngZone: NgZone, // Injecté pour synchroniser le callback externe Google
    public theme: ThemeService
  ) {}

  ngOnInit(): void {
    if (this.authService.isAuthenticated()) {
      this.router.navigate(["/welcome"]);
      return;
    }

    this.loginForm = this.fb.group({
      login: ["", [Validators.required]],
      password: ["", [Validators.required]],
    });

    this.otpForm = this.fb.group({
      otpCode: [
        "",
        [Validators.required, Validators.minLength(6), Validators.maxLength(6)],
      ],
    });
  }

  ngAfterViewInit(): void {
    this.initGoogleSSO();
  }

  private initGoogleSSO(): void {
    setTimeout(() => {
      if (typeof google !== 'undefined' && google?.accounts?.id) {
        google.accounts.id.initialize({
          client_id: this.googleClientId,
          callback: (response: any) => this.handleGoogleCallback(response)
        });

        const btnElement = document.getElementById('googleBtn');
        if (btnElement) {
          google.accounts.id.renderButton(btnElement, {
            theme: 'outline',
            size: 'large',
            width: '100%',
            text: 'continue_with'
          });
        }
      }
    }, 300);
  }

  /** Traitement optimisé dans NgZone pour une transition fluide sans lag ni chevauchement. */
  private handleGoogleCallback(response: any): void {
    if (response && response.credential) {
      // Force l'exécution dans la zone Angular
      this.ngZone.run(() => {
        this.isLoading = true;
        this.errorMessage = "";

        this.authService.loginWithGoogle(response.credential).subscribe({
          next: (res) => {
            this.isLoading = false;
            const userDisplayName = res.user?.first_name || res.user?.login || 'User';

            this.snackBar.open(
              `Welcome back, ${userDisplayName}!`,
              "Close",
              {
                duration: 3000,
                panelClass: ["snackbar-success"],
                horizontalPosition: "right",
                verticalPosition: "top",
              }
            );

            // Navigation instantanée et destruction propre du composant Login
            this.router.navigate(["/welcome"]);
          },
          error: (err) => {
            this.isLoading = false;
            this.errorMessage = err?.error?.error || err?.error?.message || "Google sign-in failed";
          }
        });
      });
    }
  }

  onSubmitLogin(): void {
    if (this.loginForm.invalid) return;

    this.isLoading = true;
    this.errorMessage = "";

    this.authService.login(this.loginForm.value).subscribe({
      next: (res) => {
        this.isLoading = false;

        if (res.require_2fa) {
          this.step = "2fa";
          this.pendingLogin = res.login || this.loginForm.value.login;
          this.anomalyScore = res.anomaly_score || 0.85;
          this.maskedEmail = res.masked_email || "your email";
          this.otpForm.reset();
          this.startTimer();
        } else if (res.success) {
          this.router.navigate(["/welcome"]);
        }
      },
      error: (err) => {
        this.isLoading = false;
        this.errorMessage = err.error?.error || err.message || "Invalid username or password";
      },
    });
  }

  onSubmitOTP(): void {
    if (this.otpForm.invalid) return;

    this.isLoading = true;
    this.errorMessage = "";
    const otpCode = this.otpForm.value.otpCode;

    this.authService.verify2FA(this.pendingLogin, otpCode).subscribe({
      next: (res) => {
        this.isLoading = false;
        if (res.success) {
          this.stopTimer();
          this.router.navigate(["/welcome"]);
        }
      },
      error: (err) => {
        this.isLoading = false;
        this.errorMessage = err.error?.error || err.message || "Invalid or expired 2FA code";
      },
    });
  }

  onResendOTP(): void {
    if (!this.canResend || this.isLoading) return;

    this.isLoading = true;
    this.errorMessage = "";

    this.authService.resend2FA(this.pendingLogin).subscribe({
      next: () => {
        this.isLoading = false;
        this.otpForm.reset();
        this.startTimer();
        this.snackBar.open(
          "A new 2FA code has been sent to your email!",
          "Close",
          {
            duration: 4000,
            panelClass: ["snackbar-success"],
            horizontalPosition: "right",
            verticalPosition: "top",
          },
        );
      },
      error: (err) => {
        this.isLoading = false;
        this.errorMessage = err.error?.error || err.message || "Failed to resend 2FA code";
      },
    });
  }

  startTimer(): void {
    this.stopTimer();
    this.countdown = 60;
    this.canResend = false;

    this.timerInterval = setInterval(() => {
      if (this.countdown > 0) {
        this.countdown--;
      } else {
        this.canResend = true;
        this.stopTimer();
      }
    }, 1000);
  }

  stopTimer(): void {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  get formattedTimer(): string {
    const minutes = Math.floor(this.countdown / 60);
    const seconds = this.countdown % 60;
    return `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
  }

  backToLogin(): void {
    this.stopTimer();
    this.step = "credentials";
    this.errorMessage = "";
    setTimeout(() => this.initGoogleSSO(), 100);
  }

  ngOnDestroy(): void {
    this.stopTimer();
  }
}