import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * KPIT wordmark, drawn as stroked paths so it stays crisp at any size and
 * follows `color` (lime by default). `compact` renders only the "K" monogram.
 */
@Component({
  selector: 'app-brand-logo',
  standalone: true,
  imports: [CommonModule],
  template: `
    <svg *ngIf="!compact" class="logo" viewBox="0 0 160 66" role="img" aria-label="KPIT"
         fill="none" stroke="currentColor" stroke-width="9">
      <path d="M12 6V40"/>
      <path d="M15 33L38 6"/>
      <path d="M17 29L41 58"/>
      <circle cx="12" cy="58" r="5.5" fill="currentColor" stroke="none"/>
      <path d="M60 60V6H73A14 14 0 0 1 73 34H60"/>
      <path d="M100 6V60"/>
      <path d="M113 6H143"/>
      <path d="M128 6V60"/>
      <circle cx="152" cy="9" r="5.5" fill="currentColor" stroke="none"/>
    </svg>
    <svg *ngIf="compact" class="logo" viewBox="0 0 54 66" role="img" aria-label="KPIT"
         fill="none" stroke="currentColor" stroke-width="9">
      <path d="M12 6V40"/>
      <path d="M15 33L38 6"/>
      <path d="M17 29L41 58"/>
      <circle cx="12" cy="58" r="5.5" fill="currentColor" stroke="none"/>
    </svg>
  `,
  styles: [`
    :host { display: inline-flex; color: var(--lime, #b9f53a); line-height: 0; }
    .logo { height: 100%; width: auto; display: block; }
  `]
})
export class BrandLogoComponent {
  @Input() compact = false;
}
