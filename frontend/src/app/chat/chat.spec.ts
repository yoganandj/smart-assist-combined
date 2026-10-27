import { ComponentFixture, TestBed } from '@angular/core/testing';
import { vi } from 'vitest';
import { Chat } from './chat';
import { Auth } from '../services/auth';

describe('Chat', () => {
  let component: Chat;
  let fixture: ComponentFixture<Chat>;
  let auth: { logout: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    auth = { logout: vi.fn() };
    await TestBed.configureTestingModule({
      imports: [Chat],
      providers: [{ provide: Auth, useValue: auth }],
    }).compileComponents();

    fixture = TestBed.createComponent(Chat);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('calls Auth.logout when the sign-out button is clicked', () => {
    const signOutButton = fixture.nativeElement.querySelector(
      'button',
    ) as HTMLButtonElement;

    signOutButton.click();

    expect(auth.logout).toHaveBeenCalledOnce();
  });
});
