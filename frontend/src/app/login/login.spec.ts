import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { Login } from './login';

describe('Login', () => {
  let component: Login;
  let fixture: ComponentFixture<Login>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Login],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(Login);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('shows the SSO option immediately without checking the current session', () => {
    const ssoLink = fixture.nativeElement.querySelector(
      'a[href="/.auth/login/aad?post_login_redirect_uri=%2Fchat"]',
    ) as HTMLAnchorElement;

    expect(ssoLink).toBeTruthy();
    expect(ssoLink.textContent).toContain('Continue with organization SSO');
  });
});
